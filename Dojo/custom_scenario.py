import os

from pydantic import BaseModel

from scenario import ScenarioModel


class CustomScenario(BaseModel):
    """A custom scenario that can be saved to and loaded from disk.
    
    Attributes:
        name: The name of the scenario
        scenario: The game state for this scenario
    """
    name: str
    scenario: ScenarioModel

    def save(self) -> None:
        """Save this scenario to disk"""
        if not self.name:
            raise ValueError("Scenario must have a name before saving")

        # Ensure the scenarios directory exists
        os.makedirs(_get_custom_scenarios_path(), exist_ok=True)

        # Save to file
        file_path = os.path.join(_get_custom_scenarios_path(), f"{self.name}.json")
        with open(file_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, name: str) -> 'CustomScenario':
        """Load a specific scenario by name"""
        file_path = os.path.join(_get_custom_scenarios_path(), f"{name}.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No scenario found with name '{name}'")

        with open(file_path, "r") as f:
            return cls.model_validate_json(f.read())


def get_custom_scenarios():
    """Get all custom scenarios"""
    custom_scenarios = {}
    for file in os.listdir(_get_custom_scenarios_path()):
        if file.endswith(".json"):
            custom_scenarios[file.replace(".json", "")] = CustomScenario.load(file.replace(".json", ""))
    return custom_scenarios


def _get_custom_scenarios_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    path = os.path.join(appdata_path, "RLDojo", "Scenarios")
    if not os.path.exists(path):
        os.makedirs(path)
    return path
