from __future__ import annotations

from coverage import Coverage


def new_coverage(filename: str | None = None) -> Coverage:
    coverage = Coverage(
        include=["*/niquests/*"],
        check_preimported=True,
        config_file=False,
        data_file=filename,
        timid=True,
    )
    coverage.set_option("run:disable_warnings", ["already-imported"])
    return coverage


def save_coverage(coverage: Coverage, preimport_coverage: Coverage) -> None:
    preimport_data = preimport_coverage.get_data()
    coverage.get_data().add_lines(
        {filename: preimport_data.lines(filename) or [] for filename in preimport_data.measured_files()}
    )
    coverage.save()
