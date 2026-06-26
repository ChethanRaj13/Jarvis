# Verification Engine — Architecture Design Document

**Project:** Windows-Native Local Personal AI Assistant  
**Document Type:** Software Architecture Document  
**Component:** Verification Engine  
**Status:** Design Phase  
**Position in System:** Follows Safety Engine and Execution Layer; precedes Completion Reporting

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Architectural Role](#2-architectural-role)
3. [Responsibilities](#3-responsibilities)
   - 3.1 Evidence Collection
   - 3.2 Filesystem Verification
   - 3.3 Registry Verification
   - 3.4 Process Verification
   - 3.5 Scheduled Task Verification
   - 3.6 Download Verification
   - 3.7 Configuration Verification
   - 3.8 Side-Effect Detection
   - 3.9 Drift Detection
   - 3.10 Verification Audit Logging
4. [Protected Verification Assets](#4-protected-verification-assets)
5. [Threat Model](#5-threat-model)
6. [Interaction with Other Components](#6-interaction-with-other-components)
7. [Design Principles](#7-design-principles)
8. [Non-Goals](#8-non-goals)
9. [Common Architectural Mistakes](#9-common-architectural-mistakes)
10. [Success Criteria](#10-success-criteria)
11. [Conclusion](#11-conclusion)

---

## 1. Purpose

The Verification Engine exists to answer one question that no other component in the system is permitted to answer:

**Did the action actually occur exactly as authorized?**

The Safety Engine determines whether an action is permitted to happen. The Execution Layer performs the action. The Verification Engine independently observes the outcome and confirms — or refutes — what the Execution Layer reports.

This distinction is not a redundancy. It is an architectural necessity.

The Execution Layer is a component that acts. It has incentive — through failure, through bugs, through manipulation — to report success even when the outcome diverges from what was authorized. The Verification Engine is a component that observes. It has no stake in the outcome. Its only function is to compare authorized intent against verified reality and produce an honest record of the difference.

A fundamental principle underlies this component:

**Execution claims are not evidence. Independent observation is evidence.**

The fact that the Execution Layer reports that a file was deleted does not constitute proof that the file no longer exists. The fact that a registry write was reported as successful does not constitute proof that the registry now reflects the authorized value. The Verification Engine is the subsystem that independently interrogates system state and produces verified evidence before any action is declared complete.

**Mission Statement:** Independently confirm that every authorized action produced exactly the system state it was authorized to produce — and that no unauthorized state changes occurred as a consequence — before that action is reported as successfully completed.

---

## 2. Architectural Role

The Verification Engine occupies the trust boundary between execution claims and verified reality. Its position in the processing pipeline is as follows:

```
AI Layer          → Decides what should happen

Safety Engine     → Decides whether it is permitted to happen

Execution Layer   → Performs what actually happens

Verification Engine → Proves what happened
```

This separation is absolute. The Verification Engine does not authorize, plan, execute, or decide. It observes, compares, and records.

The data flow through the verification boundary is:

```
Safety Engine
    ↓
  [Authorization Record + Verification Requirements]
    ↓
Execution Layer
    ↓
  [Execution Report]
    ↓
Verification Engine  ← Verification Boundary
    ↓
  [Verification Decision]
    ↓
Completion Reporting
```

No action may be reported as complete without an explicit verification decision from the Verification Engine. An authorization from the Safety Engine permits execution to begin. A verification decision from the Verification Engine is what permits completion to be reported.

The Verification Engine receives two independent inputs: the authorization record from the Safety Engine (which describes what was expected to happen) and its own independent observation of system state (which describes what actually happened). These two inputs must agree before a VERIFIED decision is produced.

The Verification Engine does not receive its evidence from the Execution Layer. It collects evidence independently.

**Architectural Domains**

At the HLD stage, the Verification Engine should be decomposed into the following architectural domains, each with distinct ownership, data boundaries, and component responsibilities:

| Domain | Responsibility |
|---|---|
| Evidence Collection Domain | Independent observation of system state; pre- and post-execution snapshots; evidence timestamping and binding |
| Verification Domain | Comparison of collected evidence against authorization record; outcome determination for each verification type |
| Side-Effect Detection Domain | Scope-aware detection of system state changes beyond the authorized action boundary |
| Drift Detection Domain | Session-level attribution of all state changes to authorized actions; unattributed change flagging |
| Audit Domain | Append-only persistence of verification records, evidence, and integrity chain maintenance |

These domains map directly to the responsibilities defined in Section 3 and serve as the bounded context boundaries for HLD decomposition. No domain may produce a VERIFIED decision independently — the final verification decision is an aggregation across all applicable domains.

**Verification Decision Model**

The Verification Engine produces one of four decisions, aligned with the Safety Engine's authorization terminology to support consistent human review workflows:

| Decision | Meaning |
|---|---|
| VERIFIED | Independent evidence confirms the action occurred exactly as authorized, with no unauthorized side effects detected. |
| FAILED | Independent evidence confirms the action did not occur as authorized, or unauthorized side effects were detected. |
| PARTIAL | The authorized scope was partially confirmed, but one or more elements could not be verified. Equivalent to incomplete authorization fulfillment. |
| ESCALATE | Evidence collection was insufficient, ambiguous, or inconclusive. Human review is required before the action may be reported as complete. |

No verification decision other than VERIFIED may be treated as a successful completion. PARTIAL and ESCALATE are not success states — they are gates that prevent completion reporting until the discrepancy is resolved.

**MVP Compatibility Note**

This architecture specifies that the Verification Engine receives explicit verification requirements generated by the Safety Engine as part of the authorization record. In the current Safety Engine MVP, dedicated verification requirement generation is not yet implemented. For MVP deployments, the Verification Engine derives its verification requirements directly from the authorization record's action type, target resource, and risk classification. This is a functional fallback — the full architecture, in which the Safety Engine produces explicit per-action verification requirements, remains the target design and should be implemented in a subsequent Safety Engine version.

---

## 3. Responsibilities

The Verification Engine holds exclusive ownership of the following responsibilities. These must not be delegated to, or duplicated in, any other component.

### 3.1 Evidence Collection

Before any verification comparison occurs, the Verification Engine must independently collect evidence of system state. Evidence is never sourced from the Execution Layer. Evidence is never sourced from the Planner. Evidence is never sourced from AI-generated output.

Evidence collection is the process by which the Verification Engine directly interrogates the host operating system, file system, registry, and process environment to observe current system state. This interrogation must occur through independent system calls — not through the same tooling that was used during execution, and not through any path that the Execution Layer controls or can influence.

Evidence collection must be time-bounded. The evidence window — the interval between execution completion and verification observation — must be defined and enforced. Evidence collected outside this window may reflect state changes caused by other processes and must be treated as unreliable.

Evidence must be captured with sufficient specificity to support comparison against the authorized outcome. A verification that confirms only that a file exists is insufficient if the authorization specified a file with particular contents, permissions, or size. Evidence collection must capture the attributes that the verification requirement demands.

### 3.2 Filesystem Verification

For every action that targets the file system, the Verification Engine must independently confirm the resulting state of the file system against the state declared in the authorization record.

Verification requirements by operation type include:

**File creation:** The Verification Engine must confirm that the file exists at the exact authorized path, that its creation timestamp is consistent with the execution window, and that no additional files were created in the same directory as unauthorized side effects.

**File deletion:** The Verification Engine must confirm that the file no longer exists at the authorized path. The absence must be confirmed through a direct file system query, not through the absence of an error code from the Execution Layer. The Verification Engine must also confirm that no backup copies, recycle bin entries, or shadow copies were created as a consequence of the deletion without authorization.

**File modification:** The Verification Engine must confirm that the file's content, size, or modification timestamp reflects the authorized change, and that only the authorized file was modified. If the authorization was scoped to a specific byte range or attribute, the verification must be scoped to that same range.

**File movement or rename:** The Verification Engine must confirm that the file no longer exists at the source path and does exist at the destination path. Both states must be independently confirmed.

**Directory operations:** Recursive or bulk operations must be verified at the scope that was authorized. A deletion of a directory requires confirmation that all authorized contents were removed and that no contents outside the authorized scope were affected.

### 3.3 Registry Verification

Registry operations require independent confirmation of the registry's state following execution. The Verification Engine must not use the same registry access tool that performed the write to confirm its result. Evidence must be collected through an independent registry query mechanism.

**Registry key creation or modification:** The Verification Engine must confirm that the key exists at the authorized path, that its value matches the authorized value exactly, that no additional keys were created in the same hive as unauthorized side effects, and that no protected registry paths were accessed during the operation.

**Registry key deletion:** The Verification Engine must confirm that the key no longer exists at the authorized path and that no unexpected keys in adjacent paths were removed.

**Protected hive operations:** Any operation near protected registry hives — particularly those associated with startup behavior, security policy, or system configuration — requires heightened verification scrutiny. The Verification Engine must capture a broader state snapshot of adjacent paths to detect drift in protected regions.

### 3.4 Process Verification

For actions that involve process management, the Verification Engine must confirm the process state as it exists after execution — not as the Execution Layer reports it.

**Process launch:** The Verification Engine must confirm that the process is running with the authorized executable path, the authorized command-line parameters, and within the authorized privilege context. A process running with elevated privileges where standard privileges were authorized is a verification failure.

**Process termination:** The Verification Engine must confirm that the targeted process is no longer running. The Verification Engine must also confirm that no child processes spawned by the target remain running as orphaned processes, unless their existence was explicitly authorized.

**Process behavior scope:** The Verification Engine must confirm that the launched or terminated process did not cause immediate side effects — such as child process creation, file system writes, or network connections — that were not included in the authorization scope.

### 3.5 Scheduled Task Verification

Scheduled task operations require particular verification rigor because their effects persist beyond the current session and can establish execution patterns that repeat without further user interaction.

**Task creation:** The Verification Engine must confirm that the task exists in the Task Scheduler with exactly the authorized parameters: the authorized trigger conditions, the authorized executable target, the authorized run frequency, and the authorized privilege level. Any deviation from the authorized parameter set is a verification failure. The Verification Engine must also confirm that no additional tasks were created as a side effect of the authorized task creation.

**Task modification:** The Verification Engine must confirm that the modified task's parameters match the authorized post-modification state exactly, and that no other tasks were modified as a consequence.

**Task deletion:** The Verification Engine must confirm that the task no longer exists in the Task Scheduler.

**Persistence detection:** For all scheduled task operations, the Verification Engine must inspect adjacent tasks to detect whether the execution created unexpected persistence mechanisms — tasks that will execute programs or scripts at system startup or on recurring intervals without explicit user authorization.

### 3.6 Download Verification

Downloaded content introduces external material into the trusted execution environment and must be verified with particular care.

**File integrity:** The Verification Engine must confirm that the downloaded file's hash matches the expected hash recorded in the authorization. If no expected hash was established at authorization time, the Verification Engine must flag this as a verification gap and escalate rather than accept the download as verified.

**File type confirmation:** The Verification Engine must confirm the actual file type of the downloaded content — not its declared MIME type or its filename extension. A file downloaded as a document that proves to be an executable is a verification failure.

**Destination confirmation:** The Verification Engine must confirm that the downloaded file was written only to the authorized destination path. Writes to additional locations are unauthorized side effects.

**Execution prevention:** The Verification Engine must confirm that the downloaded file has not been executed as part of the download operation. Download and execution are distinct authorized operations; a download that triggered execution without a separate authorization is a verification failure.

### 3.7 Configuration Verification

For actions that modify configuration files, safety policies, runtime settings, or assistant configuration, the Verification Engine must compare the post-execution configuration state against both the authorized change and the pre-execution baseline.

**Change scope confirmation:** The Verification Engine must confirm that only the authorized configuration values were modified, and that no other configuration values were changed as a consequence of the authorized change.

**Baseline comparison:** The Verification Engine must maintain a pre-execution snapshot of relevant configuration state for any operation that targets configuration. The post-execution state must be compared against this baseline to detect unauthorized drift.

**Safety-relevant configuration:** Modifications to any configuration file that governs safety behavior, authorization rules, or policy enforcement require heightened verification. The Verification Engine must confirm that the Safety Engine's own configuration files were not modified as a side effect of any authorized configuration change.

### 3.8 Side-Effect Detection

Side-effect detection is the process of confirming that authorized execution did not produce system state changes beyond the scope of the authorized action. This responsibility is distinct from outcome verification: outcome verification confirms that the authorized change occurred; side-effect detection confirms that nothing else changed.

Side-effect detection operates by comparing a pre-execution state snapshot against a post-execution state snapshot across a defined scope of observable system state. The scope must be calibrated to the action type: a file creation operation warrants side-effect checking within the containing directory; a PowerShell execution warrants broader system-wide side-effect detection.

Categories of side effects that must be detected include:

**File system side effects:** Files created, modified, or deleted in paths outside the authorized scope during the execution window.

**Registry side effects:** Registry keys created, modified, or deleted in paths outside the authorized scope during the execution window.

**Process side effects:** Processes launched or terminated outside the scope of the authorized process operation.

**Network side effects:** Outbound network connections established during the execution window that were not part of the authorized action. The Verification Engine does not block network connections — that is the Safety Engine's role — but it must detect and record unexpected network activity as a verification concern.

**Persistence side effects:** Startup entries, scheduled tasks, or registry run keys created during the execution window that were not explicitly authorized.

The Verification Engine must treat the detection of any unauthorized side effect as a PARTIAL or FAILED verification outcome, depending on the severity of the side effect. An authorized file creation that also wrote to a protected system directory is not a success with a caveat — it is a verification failure.

### 3.9 Drift Detection

Drift detection is the Verification Engine's responsibility to identify when system state diverges from the state produced by authorized operations over time. While most verification occurs immediately after execution, certain verification obligations persist beyond the immediate post-execution window.

**Authorization-to-outcome drift:** The Verification Engine must confirm that the system state at the time of verification matches the state that the authorization predicted would result from the action. Drift between the predicted outcome and the observed outcome — even when both appear benign — constitutes a verification discrepancy that must be recorded.

**Session-boundary verification:** At the conclusion of each session, the Verification Engine must confirm that the cumulative set of authorized actions accounts for all observable changes to protected assets during that session. Any system state change not traceable to an authorized action record is an unattributed change that must be flagged.

**Cumulative change tracking:** For assets that are modified multiple times during a session, the Verification Engine must track the state delta attributable to each authorized action independently, to ensure that each change is accounted for and that no unauthorized changes are embedded between authorized ones.

### 3.10 Verification Audit Logging

Every verification decision — regardless of outcome — must produce an immutable verification record. This record is the Verification Engine's primary output and the foundation of the system's accountability model.

The verification record must document: the authorization record against which verification was performed, the evidence collected to support the verification decision, the comparison method used, the outcome (VERIFIED, FAILED, PARTIAL, or ESCALATE), the rationale for the outcome, the side effects detected, and the timestamp of the evidence collection.

Verification records must be written to an append-only store before the verification decision is communicated to any other component. A verification decision that exists without a corresponding audit record is not a valid verification decision.

Verification records must be cross-referenceable against the Safety Engine's authorization records by request identifier, enabling complete reconstruction of the authorization-to-verification chain for any action.

---

## 4. Protected Verification Assets

The Verification Engine is itself an asset that must be protected. The integrity of the verification process depends on the integrity of the following assets under the Verification Engine's ownership.

### 4.1 Verification Records

The immutable post-execution evidence records produced by the Verification Engine. These records are the non-repudiable proof of what actually occurred following authorized execution. Their integrity is foundational to the system's accountability model.

**Protection requirements:** Verification records must be written to an append-only store. No component — including the Verification Engine itself — may modify or delete a verification record after it has been written. The record store must support integrity chain verification to detect tampering.

### 4.2 Evidence Store

The pre-execution state snapshots, collected execution evidence, and raw observation data that support verification decisions. This store contains the raw material from which verification decisions are derived.

**Protection requirements:** Evidence must be stored separately from execution artifacts. Evidence collection pathways must be independent of the Execution Layer. The evidence store must be protected from modification by any component other than the Verification Engine's evidence collection subsystem.

### 4.3 Execution Evidence

The specific system state observations collected immediately after execution: file system state, registry state, process list, scheduled task inventory, and network activity records. This evidence represents the ground truth of what the system looks like after an action has been performed.

**Protection requirements:** Execution evidence must be timestamped and associated with the specific authorization record it was collected to verify. Evidence must not be reusable across multiple verification sessions — each verification event must produce fresh evidence. Stale evidence must never be substituted for current observations.

### 4.4 Verification Policies

The rules that govern how verification is performed: which evidence is required for each action type, what constitutes a successful verification outcome, what side-effect detection scope applies to each operation category, and what evidence quality thresholds are required before a verification decision is produced.

**Protection requirements:** Verification policies must be externally defined and must not be modifiable at runtime. Policies must be integrity-verified at startup. A Verification Engine operating with unverifiable policies must refuse to produce VERIFIED decisions and must produce ESCALATE for all outcomes.

### 4.5 Audit Trails

The append-only log of all verification events, including successful verifications, verification failures, inconclusive outcomes, and side-effect detections. This trail is the evidentiary foundation for post-incident investigation and compliance.

**Protection requirements:** The audit trail must be append-only and integrity-chained. No verification event may be omitted from the trail, regardless of its outcome. The audit trail must be protected from modification by any component, including the Verification Engine.

### 4.6 Verification Configuration

The configuration files that govern the Verification Engine's operational behavior: evidence collection timeouts, acceptable evidence windows, side-effect detection scopes, and verification policy file locations.

**Protection requirements:** Configuration files must be protected from modification at runtime. Changes require a controlled administrative process. Configuration integrity must be verified at startup.

### 4.7 Trust Assets

The system's — and the user's — confidence that completion reports are accurate. A single verified false success is sufficient to permanently undermine trust in the system's accountability model. Unlike technical assets, trust cannot be restored through backup or recovery procedures.

**Protection requirements:** The Verification Engine must never produce a VERIFIED decision that it cannot independently support with evidence. ESCALATE outcomes must be surfaced honestly rather than resolved optimistically. False positives are as damaging as false negatives when they are later discovered.

---

## 5. Threat Model

The Verification Engine must address the following verification-specific threats. Each represents a distinct failure mode that could allow an incorrect or incomplete action to be reported as successfully completed.

### TH-V001 — False Success Reporting

**Risk: Critical**

The Execution Layer reports that an action completed successfully when the actual system state does not reflect the reported outcome. For example, a deletion operation returns a success status code but the targeted file remains on disk. The Verification Engine must independently confirm the system state rather than trusting the Execution Layer's self-reported outcome.

**Required Mitigation:** The Verification Engine must collect evidence through independent system queries that do not pass through the Execution Layer. No self-reported success from any downstream component is accepted without independent confirmation.

### TH-V002 — Evidence Tampering

**Risk: Critical**

After execution, an actor with access to the system modifies system state to create the appearance of successful authorized execution — either by manufacturing evidence that the action occurred as authorized, or by eliminating evidence that the action failed or produced unauthorized side effects.

**Required Mitigation:** Evidence must be collected within a defined and enforced time window immediately following execution. Evidence older than the authorized window must be rejected. The evidence collection timestamp must be independently recorded and included in the verification record.

### TH-V003 — Verification Bypass

**Risk: Critical**

The system is structured or manipulated such that action completion is reported without the Verification Engine being invoked. This may occur through a code path that routes completion directly from the Execution Layer to the reporting layer, or through a component that falsely produces a VERIFIED decision without performing evidence collection.

**Required Mitigation:** Action completion must be architecturally incapable of being reported without a corresponding verification record. The completion reporting system must require a valid verification record identifier before producing any success report. This must be enforced structurally, not through convention.

### TH-V004 — Partial Execution Acceptance

**Risk: High**

An action that only partially completed is reported as fully verified. For example, a bulk file deletion that removed 90% of the targeted files is accepted as VERIFIED because the primary target was deleted. Partial completion that does not match the authorized scope is a verification failure.

**Required Mitigation:** Verification must validate the complete authorized scope, not only the primary target. Any element of the authorized scope that cannot be confirmed must be reported as a partial failure. PARTIAL is not equivalent to VERIFIED.

### TH-V005 — Unauthorized Side Effect Concealment

**Risk: Critical**

An execution produces unauthorized side effects — such as creating additional files, modifying adjacent registry keys, or establishing persistence mechanisms — that are not detected by the Verification Engine because it only checks the primary authorized target.

**Required Mitigation:** Side-effect detection must be a mandatory component of every verification event. The detection scope must extend beyond the primary authorized target to cover the categories of side effects appropriate to each action type.

### TH-V006 — Drift Between Authorization and Outcome

**Risk: High**

The system state produced by execution matches the general intent of the authorization but differs in specific parameters. For example, a file was created at the authorized path but with different permissions than authorized, or a registry key was created with the authorized value but with an unauthorized type.

**Required Mitigation:** Verification must confirm the specific attributes declared in the authorization record, not only the existence of the target. Attribute-level comparison is required, not only existence confirmation.

### TH-V007 — Replay of Old Evidence

**Risk: High**

Stale evidence from a previous verification event — evidence collected during an earlier execution — is presented or accepted as current evidence for a new verification event. This may occur through a caching error, a deliberate attack, or a component that reuses evidence across multiple verification sessions.

**Required Mitigation:** All evidence must be timestamped at collection time. Evidence must be bound to the specific authorization record it was collected to support. Evidence older than the defined evidence window must be rejected unconditionally, regardless of its content.

### TH-V008 — Forged Execution Results

**Risk: Critical**

A component in the system fabricates the outputs of the Execution Layer — producing a synthetic execution report that claims success when execution either did not occur or produced different outcomes. The Verification Engine must detect this through independent evidence collection rather than trusting any execution report.

**Required Mitigation:** The Verification Engine must never consume the Execution Layer's reported outcome as an input to its verification decision. The verification decision must be produced entirely from independently collected evidence compared against the authorization record.

### TH-V009 — Verification Record Corruption

**Risk: Critical**

Verification records in the evidence store or audit trail are modified after they are written, either to conceal a verification failure or to falsely claim that a verification was performed when it was not. Corrupted verification records undermine the system's entire accountability model.

**Required Mitigation:** Verification records must be written to an append-only store with integrity chain hashing. The integrity chain must be verified at startup and periodically during operation. A detected chain gap must be treated as a critical security event. No verification record may be modified after it is written.

### TH-V010 — Verification Tool Compromise

**Risk: Critical**

The tool or mechanism used by the Verification Engine to collect evidence is the same tool that performed execution, or is subject to influence by the Execution Layer. If the Execution Layer can influence how the Verification Engine observes system state, it can cause false verifications.

**Required Mitigation:** Evidence collection must use mechanisms entirely independent of those used during execution. The Verification Engine must not share tooling, execution pathways, or API surfaces with the Execution Layer for its evidence collection operations.

### TH-V011 — Time-of-Check to Time-of-Use Race

**Risk: Medium**

System state changes between the time the Verification Engine collects evidence and the time the verification decision is recorded. Another process modifies the verified artifact immediately after verification, causing the verification record to describe a state that no longer exists.

**Required Mitigation:** The evidence collection window must be minimized. The verification decision must be produced and recorded as close in time as possible to evidence collection. Where time-of-check to time-of-use risk is elevated — for volatile resources like processes — the verification must note the temporal limitation explicitly in the verification record.

### TH-V012 — Insufficient Evidence Resolved as Verified

**Risk: High**

Evidence collected by the Verification Engine is ambiguous, incomplete, or of insufficient quality to support a definitive VERIFIED or FAILED decision, but the Verification Engine produces a VERIFIED decision anyway to avoid triggering human review.

**Required Mitigation:** ESCALATE is the required outcome when evidence quality is insufficient to produce a definitive VERIFIED or FAILED decision. ESCALATE routes the outcome to human review rather than silently resolving in favor of success. ESCALATE outcomes must never be automatically promoted to VERIFIED — they must be resolved by a human reviewer or treated as FAILED after a defined escalation timeout.

---

## 6. Interaction with Other Components

### 6.1 Safety Engine

The Safety Engine is the Verification Engine's primary upstream dependency. Every verification event is initiated by an authorization record produced by the Safety Engine. The authorization record contains the verification requirements — the specific evidence that must be collected and the specific system state that must be confirmed — that the Verification Engine is obligated to satisfy.

The relationship is one-directional at the record level: the Safety Engine produces authorization records and verification requirements; the Verification Engine consumes them. The Verification Engine does not provide feedback to the Safety Engine during the verification process. However, verification outcomes may be used over time to inform Safety Engine policy refinement — the pattern of which action types produce FAILED or PARTIAL outcomes can inform risk classification and approval thresholds.

Critically, the Safety Engine must not be involved in producing the evidence that the Verification Engine uses to verify Safety Engine-authorized actions. The two components must remain architecturally independent in their evidence handling.

### 6.2 Execution Layer

The Execution Layer is the component whose outputs the Verification Engine evaluates. The relationship is intentionally adversarial in an architectural sense: the Verification Engine treats the Execution Layer as an untrusted reporter and verifies its work through independent observation.

The Execution Layer communicates execution completion to the Verification Engine — signaling that an action has been performed and that verification should proceed. This signal initiates evidence collection. The signal itself is not evidence; it is only a trigger. The Execution Layer must not provide evidence of its own work to the Verification Engine.

The Execution Layer must be architecturally incapable of initiating completion reporting without triggering a Verification Engine evaluation. No code path should exist from execution completion to completion reporting that bypasses the Verification Engine.

### 6.3 Tool Registry

The Tool Registry provides the Verification Engine with information about which tools were used during execution and what system surfaces those tools interact with. This informs the scope of side-effect detection: a tool that interacts only with the file system warrants file system side-effect detection; a tool that also makes network calls warrants network side-effect detection.

The Tool Registry is a passive information source for the Verification Engine. It does not participate in verification decisions. Tool Registry metadata informs the verification scope but does not determine it — the Verification Engine must apply appropriate verification scope based on observed system state, not only based on declared tool capabilities.

### 6.4 Audit System

The Verification Engine produces verification records that are consumed by the system's audit infrastructure. Every verification event — including successful verifications, failures, partial verifications, and inconclusive outcomes — must be persisted to the audit system before the verification decision is communicated to any other component.

The audit system is a downstream consumer of Verification Engine output. It does not participate in verification decisions. The Verification Engine must not depend on audit system availability to perform verification; however, it must not release a verification decision until the corresponding audit record is confirmed as written.

### 6.5 Planner and Completion Reporting

The Planner and its associated reporting layer receive the Verification Engine's outcome as the signal that an action is complete. The Planner must not communicate task completion to the user until the Verification Engine has produced a VERIFIED decision. PARTIAL, FAILED, and ESCALATE outcomes must result in accurate communication to the user of what was and was not confirmed, and ESCALATE outcomes must surface a human review request rather than a completion report.

The Planner must not be able to bypass the Verification Engine to produce a completion report. Verification Engine outcomes must be the mandatory gate through which all completion reports pass. This constraint must be enforced architecturally.

---

## 7. Design Principles

The following principles must govern all Verification Engine design and implementation decisions.

**Principle 1 — Evidence Before Completion**
No action may be reported as complete until independent evidence confirming its outcome has been collected and a verification decision has been produced and recorded. Execution completion is a necessary but not sufficient condition for action completion.

**Principle 2 — Independent Verification**
Evidence must be collected through mechanisms independent of the Execution Layer. The Verification Engine must not use the same tools, APIs, or execution pathways as the Execution Layer for its evidence collection operations. Independence is not merely a preference — it is the architectural foundation of the verification trust model.

**Principle 3 — Immutable Evidence**
Collected evidence and verification records must be immutable once written. No component — including the Verification Engine — may modify a verification record or discard collected evidence after it has been stored. The immutability of evidence is what makes the verification record meaningful as a historical accountability artifact.

**Principle 4 — Deterministic Verification**
Given the same system state and the same authorization record, the Verification Engine must produce the same verification outcome. Verification decisions must not vary based on conversational context, session history, or probabilistic reasoning. Verification is a deterministic comparison, not an inference.

**Principle 5 — Fail Closed**
When the Verification Engine cannot collect sufficient evidence, cannot complete its evaluation, or encounters an error during verification, the default outcome is FAILED or ESCALATE — never VERIFIED. Ambiguity is never resolved in favor of success. An unverifiable action must not be reported as verified.

**Principle 6 — Scope Completeness**
Verification must cover the complete authorized scope, not only the primary target. A bulk operation verified only at its primary target is not fully verified. Side-effect detection is not optional — it is part of every verification event.

**Principle 7 — Separation of Authorization and Verification**
The Safety Engine authorizes. The Verification Engine verifies. These are distinct responsibilities that must remain in distinct components. The Verification Engine must not make authorization decisions, and the Safety Engine must not collect or evaluate execution evidence. Combining these responsibilities in a single component eliminates the independence that makes verification meaningful.

**Principle 8 — Honest Outcomes**
The Verification Engine must report what it found, not what would be convenient to report. ESCALATE is a valid outcome that must be surfaced rather than suppressed. A system that never produces ESCALATE outcomes is a system that is resolving uncertainty in favor of success — which is a fail-open behavior in disguise.

**Principle 9 — Full Auditability**
Every verification event must produce a complete, explainable, and reconstructible record. A reviewer must be able to understand from the verification record alone what was verified, what evidence was collected, how the comparison was performed, and why the outcome was produced.

**Principle 10 — Temporal Integrity**
Evidence has a collection timestamp, and that timestamp matters. Evidence collected outside the authorized evidence window must be rejected. The Verification Engine must enforce evidence timeliness as a verification requirement, not a preference.

---

## 8. Non-Goals

The following responsibilities are explicitly outside the scope of the Verification Engine. Assigning these functions to the Verification Engine would create inappropriate coupling and undermine both its independence and its focus.

| Responsibility | Owning Component |
|---|---|
| Deciding whether an action is permitted | Safety Engine |
| Risk classification of actions | Safety Engine |
| Policy enforcement | Safety Engine |
| Permission evaluation | Safety Engine |
| Executing actions | Execution Layer |
| Tool selection and invocation | Planner / Execution Layer |
| Task planning and step sequencing | Planner |
| Memory retrieval and context management | Memory Layer |
| Blocking unauthorized execution | Safety Engine |
| Approving or denying future similar actions based on past outcomes | Safety Engine (via policy refinement) |

The Verification Engine may detect that an action produced unauthorized side effects. It must not attempt to remediate those side effects. Remediation is an execution action that itself requires Safety Engine authorization. The Verification Engine's role is to detect, record, and report — not to act.

The Verification Engine may observe that a verified file was subsequently modified by another process. It must not treat this as a verification failure for the original action. The verification was of a specific action at a specific point in time. Subsequent changes are a separate concern.

---

## 9. Common Architectural Mistakes

The following are recurring design errors observed when implementing verification layers in AI agent systems. Each represents a pattern that must be explicitly avoided.

**Mistake 1 — Trusting Execution Claims**
Treating the Execution Layer's reported outcome as evidence. The Execution Layer is the component being verified. Its self-reported success is the exact thing the Verification Engine must not trust. Any architecture in which the Verification Engine's primary evidence source is the Execution Layer's own report is not a verification architecture — it is an acknowledgment loop.

**Mistake 2 — Verifying Through the Same Tool That Executed**
Using the same tool, API, or access mechanism for both execution and verification. If a PowerShell tool deletes a file and the same PowerShell tool is used to confirm the file's absence, the verification is only as trustworthy as the tool. An attacker or bug that causes the execution tool to lie can equally cause it to lie during verification. Independent observation pathways are mandatory.

**Mistake 3 — Mixing Authorization with Verification**
Designing the Verification Engine to consult policy rules, make risk decisions, or produce authorization-like outputs. Verification answers a factual question about system state. Authorization answers a normative question about permission. Mixing these responsibilities eliminates the architectural independence that makes verification meaningful.

**Mistake 4 — Ignoring Side Effects**
Verifying only the primary authorized target while ignoring the broader system state changes produced by execution. An action that achieved its authorized goal while also writing to a protected directory, creating a startup entry, or establishing a network connection has not succeeded in any meaningful security sense — it has produced an unauthorized outcome alongside an authorized one. Side-effect blindness is the most common verification gap in practice.

**Mistake 5 — Accepting Partial Success as Full Verification**
Treating a PARTIAL outcome as equivalent to VERIFIED when the partial completion appears satisfactory. Authorization is scoped. Verification must be equally scoped. If the authorization covered ten files and verification can only confirm nine, the verification outcome is PARTIAL, not VERIFIED. The user must be informed of the partial state.

**Mistake 6 — Auto-Resolving ESCALATE Without Human Review**
Designing the system such that ESCALATE outcomes are automatically retried or promoted to VERIFIED after a timeout, without human involvement. ESCALATE means evidence was insufficient to reach a deterministic conclusion. Retrying evidence collection that already failed to produce sufficient evidence is unlikely to produce different results, and silently resolving to VERIFIED after a timeout is a fail-open behavior. ESCALATE must route to human review; if review does not occur within a defined window, the outcome must default to FAILED, not VERIFIED.

**Mistake 7 — Allowing Verification to Lag Indefinitely**
Permitting an unconstrained time gap between execution and verification. System state changes in the interval between execution and verification introduce noise that the Verification Engine cannot distinguish from the action's effects. The evidence window must be defined and enforced. A verification that occurs thirty minutes after execution is not a verification of that execution — it is a verification of the current system state.

**Mistake 8 — Producing Verification Records After Communicating Outcomes**
Logging the verification outcome after it has been communicated to the completion reporting layer. If the audit write fails after the completion has been reported, the action appears complete with no verification record — eliminating accountability. The verification record must be written before the outcome is communicated to any downstream component.

---

## 10. Success Criteria

The Verification Engine design is considered successful when the following conditions are met:

- No action is reported as complete without a Verification Engine decision having been produced and recorded.

- Every VERIFIED decision is supported by independently collected evidence that has not passed through the Execution Layer.

- Side effects that exceed the authorized scope are detected and recorded for every verification event in which they occur.

- Verification records are immutable and cross-referenceable against Safety Engine authorization records by request identifier.

- ESCALATE and PARTIAL are valid, surfaced outcomes — not silently resolved states. ESCALATE routes to human review; PARTIAL is communicated to the user with a precise description of what could and could not be confirmed.

- Verification failures do not cause the system to enter an inconsistent state; they cause the action to be reported as unverified, with the full evidence and rationale available for review.

- The Verification Engine can be disabled, degraded, or bypassed in zero code paths that still produce VERIFIED outcomes.

- Evidence collected for one authorization event cannot be reused, replayed, or associated with a different authorization event.

- Verification records persist across session boundaries and are available for post-incident investigation.

- The Verification Engine does not, under any failure condition, produce a VERIFIED outcome when the system state does not match the authorized outcome.

---

## 11. Conclusion

The Verification Engine completes the accountability chain of the assistant system. The Safety Engine ensures that only authorized actions cross the trust boundary into execution. The Execution Layer performs those actions. The Verification Engine closes the loop by independently confirming that what was performed matches what was authorized — and that nothing beyond what was authorized occurred.

Without the Verification Engine, the system's accountability model is incomplete. Authorization records describe what was permitted. Verification records prove what actually happened. A system that can produce only the former and not the latter cannot be held accountable for execution outcomes. It can only assert intent.

The Verification Engine transforms the system's claims about its behavior into independently observable, evidence-backed facts. This is not a quality-of-life improvement. It is the architectural prerequisite for a system that a user can genuinely trust.

---

**Verification Engine — Mission Statement**

The Verification Engine exists to ensure that no action performed by the Execution Layer can be reported as successfully completed until independent evidence confirms that the system state produced by that action matches the system state authorized by the Safety Engine — and that no system state changes outside the authorized scope occurred as a consequence of that action.

Execution claims are not evidence. Independent observation is evidence. Completion requires verification.

---

*Document Type: Software Architecture Document — Design Phase*  
*Component: Verification Engine*  
*System: Windows-Native Local Personal AI Assistant*  
*Version: 1.0*
