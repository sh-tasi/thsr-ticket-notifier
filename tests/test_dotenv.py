import os
from thsr_notifier.dotenv import load_dotenv


def test_loads_values_without_overriding_existing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('THSR_T_A=1\nTHSR_T_B="two"\n# comment line\n\n', encoding="utf-8")
    monkeypatch.delenv("THSR_T_A", raising=False)
    monkeypatch.setenv("THSR_T_B", "preset")
    load_dotenv(str(env))
    assert os.environ.get("THSR_T_A") == "1"
    assert os.environ.get("THSR_T_B") == "preset"  # 既有環境變數不被覆蓋
    monkeypatch.delenv("THSR_T_A", raising=False)


def test_missing_file_is_noop(tmp_path):
    load_dotenv(str(tmp_path / "nope.env"))  # 不應拋例外
