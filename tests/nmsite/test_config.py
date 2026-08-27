from nmsite.config import configs


def test_s1_is_hybrid():
    assert configs["S1"].time_input_mode == "hybrid"


def test_s2_is_legacy():
    assert configs["S2"].time_input_mode == "legacy"


def test_dev_is_experimental():
    assert configs["DEV"].time_input_mode == "experimental"


def test_dev_hybrid_preset_exists_for_tests():
    assert configs["DEV_HYBRID"].time_input_mode == "hybrid"
    assert configs["DEV_HYBRID"].dev is True
