import typer
import questionary
from typing import Optional

from continuousbench.generators.system_generator import SystemGenerator
from continuousbench.generators.experiment_generator import ExperimentGenerator
from continuousbench.generators.test_generator import TestGenerator
from continuousbench.execution.runner import BenchmarkRunner
from continuousbench.reporting.engine import ReportingEngine
from continuousbench.validators.benchmark_validator import BenchmarkValidator
from continuousbench.utils.config import ConfigManager

app = typer.Typer(
    name="continus-bench",
    help="Continus Bench — Continuous benchmarking and regression analysis for HPC systems",
    add_completion=False,
)


@app.command()
def add_system():
    """Interactive: onboard a new HPC system."""
    generator = SystemGenerator()
    config = generator.interactive_onboard()
    if config:
        typer.echo(f"System config written to: {config}")
    else:
        typer.echo("System onboarding cancelled.", err=True)
        raise typer.Exit(1)


@app.command()
def add_experiment():
    """Interactive: create a new experiment definition."""
    generator = ExperimentGenerator()
    experiment = generator.interactive_create()
    if experiment:
        typer.echo(f"Experiment definition written to: {experiment}")
    else:
        typer.echo("Experiment creation cancelled.", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    experiment: str = typer.Argument(..., help="Experiment name or path to YAML spec"),
    system: Optional[str] = typer.Option(None, "--system", "-s", help="Target system (name:partition)"),
    environ: Optional[str] = typer.Option(None, "--environ", "-e", help="Programming environment"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Print commands without executing"),
):
    """Run a benchmark experiment."""
    runner = BenchmarkRunner()
    result = runner.run_experiment(
        experiment=experiment,
        system=system,
        environ=environ,
        dry_run=dry_run,
    )
    if result:
        typer.echo(f"Experiment completed. Report: {result}")
    else:
        typer.echo("Experiment failed.", err=True)
        raise typer.Exit(1)


@app.command()
def report(
    report_file: str = typer.Argument(..., help="Path to ReFrame JSON report"),
    output: str = typer.Option("report.html", "--output", "-o", help="Output file path"),
    fmt: str = typer.Option("html", "--format", "-f", help="Output format (html, csv, json)"),
):
    """Generate a report from a ReFrame JSON report."""
    engine = ReportingEngine()
    result = engine.generate(report_file, output, fmt)
    if result:
        typer.echo(f"Report generated: {result}")
    else:
        typer.echo("Report generation failed.", err=True)
        raise typer.Exit(1)


@app.command()
def compare(
    run_a: str = typer.Argument(..., help="First run report (JSON)"),
    run_b: str = typer.Argument(..., help="Second run report (JSON)"),
    output: str = typer.Option("comparison.html", "--output", "-o", help="Output file"),
):
    """Compare two benchmark runs."""
    engine = ReportingEngine()
    result = engine.compare(run_a, run_b, output)
    if result:
        typer.echo(f"Comparison written to: {result}")
    else:
        typer.echo("Comparison failed.", err=True)
        raise typer.Exit(1)


@app.command()
def validate(
    path: str = typer.Argument(..., help="Path to benchmark YAML spec or test file"),
):
    """Validate a benchmark specification."""
    validator = BenchmarkValidator()
    valid, errors = validator.validate_file(path)
    if valid:
        typer.echo("Benchmark spec is valid.")
    else:
        typer.echo("Validation errors:", err=True)
        for err in errors:
            typer.echo(f"  - {err}", err=True)
        raise typer.Exit(1)


@app.command()
def generate_tests(
    spec: str = typer.Argument(..., help="Path to YAML benchmark spec"),
    output_dir: str = typer.Option(".", "--output-dir", "-o", help="Output directory for generated tests"),
):
    """Generate ReFrame test files from a YAML benchmark spec."""
    generator = TestGenerator()
    files = generator.generate_from_spec(spec, output_dir)
    typer.echo(f"Generated {len(files)} test file(s):")
    for f in files:
        typer.echo(f"  {f}")


@app.command()
def list_systems():
    """List configured HPC systems."""
    config = ConfigManager()
    systems = config.list_systems()
    if not systems:
        typer.echo("No systems configured.")
        return
    for name, info in systems.items():
        parts = info.get("partitions", [])
        if parts and isinstance(parts[0], dict):
            partitions = ", ".join(p.get("name", str(p)) for p in parts)
        else:
            partitions = ", ".join(str(p) for p in parts)
        typer.echo(f"{name}: [{partitions}]")


def main():
    app()


if __name__ == "__main__":
    main()
