from verification_engine.security.startup.restricted_mode_enforcer import (
    RestrictedModeEnforcer,
    RestrictedModeState,
)


def test_restricted_mode_enable_and_disable():
    enforcer = RestrictedModeEnforcer()

    assert enforcer.is_restricted() is False
    assert enforcer.status().state == RestrictedModeState.NORMAL

    enabled = enforcer.enable()
    assert enabled.is_restricted is True
    assert enforcer.is_restricted() is True

    disabled = enforcer.disable()
    assert disabled.is_restricted is False
    assert enforcer.status().state == RestrictedModeState.NORMAL


def test_restricted_mode_initial_state():
    enforcer = RestrictedModeEnforcer(initial_state=RestrictedModeState.RESTRICTED)

    assert enforcer.is_restricted() is True
    assert enforcer.status().state == RestrictedModeState.RESTRICTED
