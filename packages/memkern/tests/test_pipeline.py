import numpy as np
from memkern import full_diagnosis, zoo

def test_pipeline_drude():
    k = zoo.drude(lam=1.0, gamma=1.0); tau = np.linspace(0,15,300)
    r = full_diagnosis(tau, k.C(tau))
    assert r["steps"]["embeddability"]["regime"] == "rational-embeddable"
    assert r["steps"]["cptp"]["cp_divisible"] is True
    assert "MET applies" in r["summary"]

def test_pipeline_underdamped_not_cp():
    k = zoo.underdamped(lam=1.0, w0=3.0, gamma=0.15); tau = np.linspace(0,25,800)
    r = full_diagnosis(tau, k.C(tau), t_max=25)
    assert r["steps"]["cptp"]["cp_divisible"] is False
    assert r["steps"]["lindblad_gap"]["integrated_gap"] > 0

def test_pipeline_subohmic_aborts_cleanly():
    k = zoo.subohmic(); tau = np.linspace(0,50,512)
    r = full_diagnosis(tau, k.C(tau))
    assert "sub-ohmic" in r["summary"]
    assert "cptp" not in r["steps"]
