import re
from pathlib import Path
from typing import Dict, Generator, Any

import yaml
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv


def _load_configs(base_dir: Path) -> Dict[str, Any]:
    load_dotenv()
    agents_config_path = base_dir / "config" / "agents.yaml"
    tasks_config_path = base_dir / "config" / "tasks.yaml"

    with open(agents_config_path, "r") as file:
        agents_config = yaml.safe_load(file)

    with open(tasks_config_path, "r") as file:
        tasks_config = yaml.safe_load(file)

    return {"agents": agents_config, "tasks": tasks_config}


def _build_agents(agents_cfg: Dict[str, Any]):
    spamfilter = Agent(config=agents_cfg["spamfilter"], allow_delegation=False, verbose=True)
    analyst = Agent(config=agents_cfg["analyst"], allow_delegation=False, verbose=True)
    scriptwriter = Agent(config=agents_cfg["scriptwriter"], allow_delegation=False, verbose=True)
    formatter = Agent(config=agents_cfg["formatter"], allow_delegation=False, verbose=True)
    scorer = Agent(config=agents_cfg["scorer"], allow_delegation=False, verbose=True)
    return spamfilter, analyst, scriptwriter, formatter, scorer


def generate_screenplay(discussion: str) -> Dict[str, Any]:
    """
    Run the screenplay pipeline and return the formatted script and score.
    """
    base_dir = Path(__file__).resolve().parents[1]
    cfg = _load_configs(base_dir)
    agents_cfg, tasks_cfg = cfg["agents"], cfg["tasks"]

    spamfilter, analyst, scriptwriter, formatter, scorer = _build_agents(agents_cfg)

    # Inject discussion into templated task descriptions
    t0_desc = str(tasks_cfg["task0"]["description"]).replace("{{discussion}}", discussion)
    t1_desc = str(tasks_cfg["task1"]["description"]).replace("{{discussion}}", discussion)

    task0 = Task(
        description=t0_desc,
        expected_output=tasks_cfg["task0"]["expected_output"],
        agent=spamfilter,
    )

    result0 = task0.execute()
    if isinstance(result0, str) and "STOP" in result0:
        return {"filtered": True, "reason": "Spam or vulgar content detected", "success": True}

    task1 = Task(
        description=t1_desc,
        expected_output=tasks_cfg["task1"]["expected_output"],
        agent=analyst,
    )

    task2 = Task(
        description=tasks_cfg["task2"]["description"],
        expected_output=tasks_cfg["task2"]["expected_output"],
        agent=scriptwriter,
    )

    task3 = Task(
        description=tasks_cfg["task3"]["description"],
        expected_output=tasks_cfg["task3"]["expected_output"],
        agent=formatter,
    )

    crew = Crew(
        agents=[analyst, scriptwriter, formatter],
        tasks=[task1, task2, task3],
        verbose=2,
        process=Process.sequential,
    )

    result = crew.kickoff()

    # Remove bracketed directions
    cleaned = re.sub(r"\(.*?\)", "", result)

    # Score
    task4 = Task(
        description=str(tasks_cfg["task4"]["description"]).replace("{{script}}", cleaned),
        expected_output=tasks_cfg["task4"]["expected_output"],
        agent=scorer,
    )

    score_raw = task4.execute()
    score_line = score_raw.split("\n")[0] if isinstance(score_raw, str) else str(score_raw)

    return {"script": cleaned, "score": score_line, "success": True}


def generate_screenplay_stream(discussion: str) -> Generator[Dict[str, Any], None, None]:
    """Simple streaming: first yield script, then yield score."""
    result = generate_screenplay(discussion)
    yield {"content": result.get("script", "")}
    yield {"content": f"Score: {result.get('score', '')}"}


