"""Remove only the exact reviewed warning change for older historical checks."""

FAIL = "Unreviewed required-field warning"
PORTAL, CATALOGUE = "static/portal/portal.js", "static/portal/portal-i18n.js"
KEY = "portal.form.requiredWarning"
OLD = 'showToast("Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.", "warning");'
NEW = 'showToast(uiText("portal.form.requiredWarning", "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục."), "warning");'
ADDITIONS = (
    '  MESSAGES.vi["portal.form.requiredWarning"] = "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.";\n'
    '  MESSAGES.en["portal.form.requiredWarning"] = "Complete the required fields before continuing.";\n'
    '  MESSAGES.zh["portal.form.requiredWarning"] = "请先填写必填项，然后继续。";\n\n'
)


def required_warning_historical_source(source: str, file: str) -> str:
    assert isinstance(source, str) and isinstance(file, str), FAIL
    if file not in (PORTAL, CATALOGUE) or KEY not in source:
        return source
    if file == PORTAL:
        assert source.count(KEY) == 1 and source.count(NEW) == 1, FAIL
        start = source.find("  function dispatchAction(source, context) {")
        at = source.find(NEW)
        end = source.find("  function bindInteractions() {")
        assert 0 <= start < at < end, FAIL
        return source.replace(NEW, OLD, 1)
    assert source.count(KEY) == 3 and source.count(ADDITIONS) == 1, FAIL
    assert source.count(ADDITIONS + "  verifyEqualKeysets();") == 1, FAIL
    return source.replace(ADDITIONS, "", 1)
