.PHONY: profile db-up demo-data ingest-demo ingest marts analyse export checks test demo

db-up:
	docker compose up -d db

demo-data:
	python -m src.make_demo_data

ingest-demo:
	python -m src.ingest --source data/demo

ingest:
	python -m src.ingest --source data/raw

marts:
	python -m src.build_marts

analyse:
	python -m src.analysis

export:
	python -m src.export_for_powerbi

checks:
	python -m src.checks

test:
	pytest -q

# Whole pipeline on synthetic data (for testing only, results are NOT real)
# Demo outputs go to outputs/demo and data/demo/exports so real results are never overwritten.
# NOTE: the demo still loads into the same database as the real data (see README).
demo: demo-data ingest-demo marts checks
	OUTPUT_DIR=outputs/demo EXPORT_DIR=data/demo/exports python -m src.analysis
	OUTPUT_DIR=outputs/demo EXPORT_DIR=data/demo/exports python -m src.export_for_powerbi

# Real reference data only (no prescribing needed): loads GP/LSOA, IMD, QOF and profiles them
profile:
	python -m src.ingest --source data/raw --reference-only
	python -m src.profile_reference
