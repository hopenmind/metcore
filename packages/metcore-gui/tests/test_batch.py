"""Headless tests for the batch core and XML export - no Qt, no display."""
import os, csv
import xml.etree.ElementTree as ET
import numpy as np
from metcore_gui.batch import run_batch, load_jobs_csv
from metcore_gui.ng_panel import NGController
from metcore_export import export_xml, result_to_dict


def test_run_batch_writes_png_and_xml(tmp_path):
    jobs = [
        {"name": "revival_demo", "channel": "revival", "gamma": 0.1, "omega": 2.0,
         "t_max": 8.0, "n_points": 256},
        {"name": "dephasing_demo", "channel": "dephasing", "gamma": 0.5,
         "t_max": 6.0, "n_points": 256},
    ]
    rep = run_batch(NGController(), jobs, tmp_path,
                    formats=["png300"], write_xml=True, name_pattern="{name}")
    assert rep.n_jobs == 2 and rep.n_ok == 2 and rep.n_failed == 0
    assert (tmp_path / "revival_demo_png300.png").is_file()
    assert (tmp_path / "revival_demo.xml").is_file()
    assert (tmp_path / "dephasing_demo.xml").is_file()
    # the xml parses and carries the verdict
    root = ET.parse(tmp_path / "revival_demo.xml").getroot()
    assert root.find("verdict") is not None


def test_name_pattern_uses_params(tmp_path):
    jobs = [{"channel": "revival", "gamma": 0.1, "omega": 2.0, "t_max": 6, "n_points": 128}]
    rep = run_batch(NGController(), jobs, tmp_path, formats=["png300"],
                    write_xml=False, name_pattern="{index}_{channel}_g{gamma}")
    assert rep.n_ok == 1
    files = os.listdir(tmp_path)
    assert any(f.startswith("0_revival_g0.1") for f in files), files


def test_one_bad_job_does_not_kill_batch(tmp_path):
    jobs = [
        {"name": "ok", "channel": "revival", "gamma": 0.1, "omega": 2.0, "t_max": 6, "n_points": 128},
        {"name": "bad", "channel": "does_not_exist", "gamma": 0.1},
    ]
    rep = run_batch(NGController(), jobs, tmp_path, formats=["png300"], write_xml=False)
    assert rep.n_ok == 1 and rep.n_failed == 1
    assert rep.jobs[1]["error"] is not None


def test_load_jobs_csv(tmp_path):
    p = tmp_path / "jobs.csv"
    p.write_text("name,channel,gamma,omega\na,revival,0.1,2.0\nb,dephasing,0.5,\n", encoding="utf-8")
    jobs = load_jobs_csv(p)
    assert len(jobs) == 2
    assert jobs[0] == {"name": "a", "channel": "revival", "gamma": 0.1, "omega": 2.0}
    assert "omega" not in jobs[1]            # empty cell dropped
    assert jobs[1]["gamma"] == 0.5


def test_export_xml_summarizes_large_arrays(tmp_path):
    r = NGController().compute(channel="revival", t_max=6, n_points=512)
    path = export_xml(r, tmp_path, "ng")
    assert path.is_file()
    root = ET.parse(path).getroot()
    # n_g scalar present, big array summarized not dumped
    assert root.find("n_g") is not None
    vol = root.find("volume")
    assert vol is not None and vol.find("_array") is not None
