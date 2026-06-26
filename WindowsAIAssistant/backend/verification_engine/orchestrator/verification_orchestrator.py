from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from WindowsAIAssistant.backend.verification_engine.contracts import (
    DriftReport,
    EvidencePackage,
    SideEffectReport,
    VerificationDecision,
    VerificationDecisionEnum,
    VerificationResult,
)
from WindowsAIAssistant.backend.verification_engine.decision import DecisionAggregator, EscalationEngine, EscalationPlan, PrecedenceResolver
from WindowsAIAssistant.backend.verification_engine.drift import DriftAccumulator, DriftAttributor, DriftReportBuilder
from WindowsAIAssistant.backend.verification_engine.side_effects import SideEffectClassifier, SideEffectDetector, SideEffectReportBuilder

from .execution_context import ExecutionContext
from .pipeline import ExecutionPipeline, PipelineResult, PipelineState, PipelineStep
from .state_machine import OrchestratorState, StateMachine


@dataclass(frozen=True)
class VerificationPipelineData:
    context: ExecutionContext
    state_machine: StateMachine = StateMachine()
    evidence_packages: tuple[EvidencePackage, ...] = ()
    validation_results: tuple[Any, ...] = ()
    verification_results: tuple[VerificationResult, ...] = ()
    side_effect_report: SideEffectReport | None = None
    drift_report: DriftReport | None = None
    decision_context: Any | None = None
    precedence_resolution: Any | None = None
    escalation_plan: EscalationPlan | None = None
    decision: VerificationDecision | None = None


@dataclass(frozen=True)
class VerificationOutcome:
    decision: VerificationDecision
    escalation_plan: EscalationPlan | None
    pipeline_state: PipelineState
    completed_steps: tuple[str, ...]
    fail_closed: bool = False
    error: str | None = None


class VerificationOrchestrator:
    def __init__(
        self,
        *,
        collectors: tuple[Any, ...] = (),
        validation_service: Any | None = None,
        verifiers: tuple[Any, ...] = (),
        side_effect_detector: SideEffectDetector | None = None,
        side_effect_classifier: SideEffectClassifier | None = None,
        side_effect_report_builder: SideEffectReportBuilder | None = None,
        drift_accumulator: DriftAccumulator | None = None,
        drift_attributor: DriftAttributor | None = None,
        drift_report_builder: DriftReportBuilder | None = None,
        decision_aggregator: DecisionAggregator | None = None,
        precedence_resolver: PrecedenceResolver | None = None,
        escalation_engine: EscalationEngine | None = None,
        pipeline: ExecutionPipeline | None = None,
    ) -> None:
        self._collectors = collectors
        self._validation_service = validation_service
        self._verifiers = verifiers
        self._side_effect_detector = side_effect_detector or SideEffectDetector()
        self._side_effect_classifier = side_effect_classifier or SideEffectClassifier()
        self._side_effect_report_builder = side_effect_report_builder or SideEffectReportBuilder()
        self._drift_accumulator = drift_accumulator or DriftAccumulator()
        self._drift_attributor = drift_attributor or DriftAttributor()
        self._drift_report_builder = drift_report_builder or DriftReportBuilder()
        self._decision_aggregator = decision_aggregator or DecisionAggregator()
        self._precedence_resolver = precedence_resolver or PrecedenceResolver()
        self._escalation_engine = escalation_engine or EscalationEngine()
        self._pipeline = pipeline or ExecutionPipeline()

    def execute(self, context: ExecutionContext) -> VerificationOutcome:
        initial = VerificationPipelineData(context=context)
        steps = (
            PipelineStep("collect", self._collect),
            PipelineStep("validate", self._validate),
            PipelineStep("verify", self._verify),
            PipelineStep("analyze", self._analyze),
            PipelineStep("decide", self._decide),
            PipelineStep("complete", self._complete),
        )
        result = self._pipeline.run(initial, steps)
        if result.state == PipelineState.COMPLETED:
            return VerificationOutcome(
                decision=result.value.decision,
                escalation_plan=result.value.escalation_plan,
                pipeline_state=result.state,
                completed_steps=result.completed_steps,
            )
        return self._fail_closed(context, result)

    def _collect(self, data: VerificationPipelineData) -> VerificationPipelineData:
        state = data.state_machine.transition(OrchestratorState.COLLECTING)
        evidence = tuple(collector.collect(request) for collector, request in zip(self._collectors, data.context.collection_requests))
        if self._collectors and len(evidence) != len(self._collectors):
            raise ValueError("collector count does not match collection request count")
        return replace(data, state_machine=state, evidence_packages=evidence)

    def _validate(self, data: VerificationPipelineData) -> VerificationPipelineData:
        state = data.state_machine.transition(OrchestratorState.VALIDATING)
        if self._validation_service is None:
            return replace(data, state_machine=state)
        results = tuple(
            self._validation_service.validate(evidence, data.context.validation_context)
            for evidence in data.evidence_packages
        )
        if any(getattr(result, "fail_closed", False) or not getattr(result, "passed", True) for result in results):
            raise ValueError("evidence validation failed closed")
        return replace(data, state_machine=state, validation_results=results)

    def _verify(self, data: VerificationPipelineData) -> VerificationPipelineData:
        state = data.state_machine.transition(OrchestratorState.VERIFYING)
        results: list[VerificationResult] = []
        for verifier, evidence in zip(self._verifiers, data.evidence_packages):
            results.append(verifier.verify(data.context.authorization, evidence))
        if self._verifiers and len(results) != len(self._verifiers):
            raise ValueError("verifier count does not match evidence count")
        return replace(data, state_machine=state, verification_results=tuple(results))

    def _analyze(self, data: VerificationPipelineData) -> VerificationPipelineData:
        state = data.state_machine.transition(OrchestratorState.ANALYZING)
        detections = tuple(self._side_effect_detector.detect(result) for result in data.verification_results)
        effects = tuple(effect for detection in detections for effect in detection.effects)
        classification = self._side_effect_classifier.classify(effects)
        side_effect_report = self._side_effect_report_builder.build(
            request_id=data.context.request.request_id,
            effects=effects,
            classification=classification.classification,
            detection_scope=str(data.context.execution_metadata.get("detection_scope", "verification result analysis")),
        )
        accumulation = self._drift_accumulator.accumulate(data.verification_results)
        attribution = self._drift_attributor.attribute(accumulation)
        drift_report = self._drift_report_builder.build(
            session_id=data.context.request.session_id,
            request_id=data.context.request.request_id,
            attribution=attribution,
            session_boundary_verified=None,
        )
        return replace(data, state_machine=state, side_effect_report=side_effect_report, drift_report=drift_report)

    def _decide(self, data: VerificationPipelineData) -> VerificationPipelineData:
        state = data.state_machine.transition(OrchestratorState.DECIDING)
        decision_context = self._decision_aggregator.aggregate(
            request_id=data.context.request.request_id,
            verification_results=data.verification_results,
            side_effect_report=data.side_effect_report,
            drift_report=data.drift_report,
        )
        resolution = self._precedence_resolver.resolve(decision_context)
        escalation_plan = self._escalation_engine.determine(decision_context, resolution)
        decision = self._decision_aggregator._build_decision(decision_context, resolution)
        return replace(
            data,
            state_machine=state,
            decision_context=decision_context,
            precedence_resolution=resolution,
            escalation_plan=escalation_plan,
            decision=decision,
        )

    def _complete(self, data: VerificationPipelineData) -> VerificationPipelineData:
        return replace(data, state_machine=data.state_machine.transition(OrchestratorState.COMPLETED))

    def _fail_closed(self, context: ExecutionContext, result: PipelineResult) -> VerificationOutcome:
        now = datetime.now(timezone.utc)
        source_id = uuid4()
        decision = VerificationDecision(
            decision_id=uuid4(),
            request_id=context.request.request_id,
            final_decision=VerificationDecisionEnum.ESCALATE,
            controlling_results=[source_id],
            full_rationale=f"orchestration failed closed at {result.failed_step}: {result.error}",
            all_results=[source_id],
            decision_timestamp=now,
            decision_engine_version="orchestrator-fail-closed-v1",
            escalation_expiry=now + timedelta(minutes=30),
        )
        return VerificationOutcome(
            decision=decision,
            escalation_plan=None,
            pipeline_state=result.state,
            completed_steps=result.completed_steps,
            fail_closed=True,
            error=str(result.error),
        )
