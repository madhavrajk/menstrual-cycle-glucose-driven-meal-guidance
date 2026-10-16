"""End-to-end smoke test on a small synthetic cohort."""

from mealguide import paths, pipeline, synthetic


def test_baselines_run_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SYNTHETIC", tmp_path / "synthetic")
    monkeypatch.setattr(paths, "RESULTS", tmp_path / "results")
    paths.SYNTHETIC.mkdir()
    for name, df in synthetic.generate(n_participants=4, n_days=30).items():
        df.to_csv(paths.SYNTHETIC / f"{name}.csv", index=False)

    results = pipeline.run_baselines(synthetic=True)

    assert len(results) == 10  # 5 targets x 2 baselines
    assert (paths.RESULTS / "baselines_synthetic.csv").exists()
    glucose = results[results["target"] == "next-day high_cv"]
    assert glucose["n_participants"].eq(4).all()
    assert glucose["auroc"].notna().all()
