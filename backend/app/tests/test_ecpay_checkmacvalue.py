"""ECPay CheckMacValue 邊界值測試。驗證 _compute_checkmac 與 verify_webhook_checkmac。"""

from __future__ import annotations

from app.providers.ecpay import (
    _compute_checkmac,
    _ecpay_url_encode,
    verify_webhook_checkmac,
)

HASH_KEY = "5294y06JbISpM5x9"
HASH_IV = "v77hoKGq4kWxNNIS"


# ---------------------------------------------------------------------------
# _ecpay_url_encode edge cases
# ---------------------------------------------------------------------------


def test_url_encode_tilde_encoded() -> None:
    """~ 必須編碼為 %7e（非保留）。"""
    result = _ecpay_url_encode("test~value")
    assert "%7e" not in result.lower() or "%7E" not in result
    # After lowercasing, ~ → %7E → lower to %7e, then .NET replacements don't touch it
    assert "~" not in result


def test_url_encode_special_chars_preserved() -> None:
    """- _ . ! * ( ) 不被編碼。"""
    result = _ecpay_url_encode("-_.*!()")
    assert "-" in result
    assert "_" in result
    assert "." in result
    assert "!" in result
    assert "*" in result
    assert "(" in result
    assert ")" in result


def test_url_encode_spaces_become_plus() -> None:
    """空格編碼為 +（非 %20）。"""
    result = _ecpay_url_encode("hello world")
    assert "+" in result
    assert "%20" not in result


def test_url_encode_chinese_characters() -> None:
    """中文字元應被正確 URL 編碼。"""
    result = _ecpay_url_encode("活動票券")
    assert "%" in result  # 有被編碼
    assert "活" not in result


# ---------------------------------------------------------------------------
# _compute_checkmac edge cases
# ---------------------------------------------------------------------------


def test_compute_checkmac_basic_deterministic() -> None:
    """同樣參數應產生相同 CheckMacValue。"""
    params = {"MerchantID": "2000132", "TotalAmount": "100", "TradeDesc": "test"}
    mac1 = _compute_checkmac(params, HASH_KEY, HASH_IV)
    mac2 = _compute_checkmac(params, HASH_KEY, HASH_IV)
    assert mac1 == mac2
    assert len(mac1) == 64  # SHA256 hex = 64 chars
    assert mac1 == mac1.upper()  # 全大寫


def test_compute_checkmac_excludes_checkmacvalue_key() -> None:
    """參數中的 CheckMacValue key 應被排除，不影響計算。"""
    params = {"MerchantID": "2000132", "TotalAmount": "100"}
    params_with_mac = {**params, "CheckMacValue": "SHOULD_BE_IGNORED"}
    mac1 = _compute_checkmac(params, HASH_KEY, HASH_IV)
    mac2 = _compute_checkmac(params_with_mac, HASH_KEY, HASH_IV)
    assert mac1 == mac2


def test_compute_checkmac_case_insensitive_sorting() -> None:
    """key 排序不區分大小寫。"""
    params1 = {"aField": "1", "BField": "2", "cField": "3"}
    params2 = {"BField": "2", "cField": "3", "aField": "1"}
    mac1 = _compute_checkmac(params1, HASH_KEY, HASH_IV)
    mac2 = _compute_checkmac(params2, HASH_KEY, HASH_IV)
    assert mac1 == mac2


def test_compute_checkmac_empty_values_excluded_when_flag() -> None:
    """exclude_empty=True 時，空值參數不參與計算。"""
    params_with_empty = {"MerchantID": "2000132", "OptionalField": "", "NullField": "None"}
    params_without_empty = {"MerchantID": "2000132", "NullField": "None"}
    mac1 = _compute_checkmac(params_with_empty, HASH_KEY, HASH_IV, exclude_empty=True)
    mac2 = _compute_checkmac(params_without_empty, HASH_KEY, HASH_IV, exclude_empty=True)
    assert mac1 == mac2


def test_compute_checkmac_empty_values_included_by_default() -> None:
    """exclude_empty=False（默認）時，空值參數參與計算。"""
    params_with_empty = {"MerchantID": "2000132", "EmptyField": ""}
    params_without_empty = {"MerchantID": "2000132"}
    mac1 = _compute_checkmac(params_with_empty, HASH_KEY, HASH_IV, exclude_empty=False)
    mac2 = _compute_checkmac(params_without_empty, HASH_KEY, HASH_IV, exclude_empty=False)
    assert mac1 != mac2


def test_compute_checkmac_different_keys_produce_different_mac() -> None:
    """不同的 HashKey/HashIV 應產生不同結果。"""
    params = {"MerchantID": "2000132"}
    mac1 = _compute_checkmac(params, "key_aaa", "iv_aaa")
    mac2 = _compute_checkmac(params, "key_bbb", "iv_bbb")
    assert mac1 != mac2


def test_compute_checkmac_integer_values_converted() -> None:
    """整數值應被轉為字串參與計算。"""
    params_int = {"TotalAmount": 100}
    params_str = {"TotalAmount": "100"}
    mac1 = _compute_checkmac(params_int, HASH_KEY, HASH_IV)
    mac2 = _compute_checkmac(params_str, HASH_KEY, HASH_IV)
    assert mac1 == mac2


# ---------------------------------------------------------------------------
# verify_webhook_checkmac edge cases
# ---------------------------------------------------------------------------


def test_verify_returns_false_when_no_checkmacvalue() -> None:
    """缺少 CheckMacValue 應回傳 False。"""
    params = {"MerchantID": "2000132", "RtnCode": "1"}
    assert verify_webhook_checkmac(params, HASH_KEY, HASH_IV) is False


def test_verify_returns_false_when_empty_checkmacvalue() -> None:
    """空字串 CheckMacValue 應回傳 False。"""
    params = {"MerchantID": "2000132", "RtnCode": "1", "CheckMacValue": ""}
    assert verify_webhook_checkmac(params, HASH_KEY, HASH_IV) is False


def test_verify_returns_false_when_wrong_checkmacvalue() -> None:
    """錯誤的 CheckMacValue 應回傳 False。"""
    params = {"MerchantID": "2000132", "RtnCode": "1", "CheckMacValue": "WRONGMAC123"}
    assert verify_webhook_checkmac(params, HASH_KEY, HASH_IV) is False


def test_verify_returns_true_when_correct_checkmacvalue() -> None:
    """正確的 CheckMacValue 應回傳 True。"""
    params = {"MerchantID": "2000132", "RtnCode": "1", "TotalAmount": "100"}
    correct_mac = _compute_checkmac(params, HASH_KEY, HASH_IV, exclude_empty=False)
    params["CheckMacValue"] = correct_mac
    assert verify_webhook_checkmac(params, HASH_KEY, HASH_IV) is True


def test_verify_whitespace_trimmed() -> None:
    """CheckMacValue 前後空白應被忽略。"""
    params = {"MerchantID": "2000132"}
    correct_mac = _compute_checkmac(params, HASH_KEY, HASH_IV, exclude_empty=False)
    params["CheckMacValue"] = f"  {correct_mac}  "
    assert verify_webhook_checkmac(params, HASH_KEY, HASH_IV) is True
