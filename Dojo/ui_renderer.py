from typing import Optional

from dojo_state import DojoState, GymMode, ScenarioPhase, CUSTOM_MODES
from constants import (
    SCORE_BOX_START_X, SCORE_BOX_START_Y, SCORE_BOX_WIDTH, SCORE_BOX_HEIGHT,
    CUSTOM_MODE_MENU_START_X, CUSTOM_MODE_MENU_START_Y, CUSTOM_MODE_MENU_WIDTH, CUSTOM_MODE_MENU_HEIGHT,
    CONTROLS_MENU_WIDTH, CONTROLS_MENU_HEIGHT
)
import utils
from scenario import ScenarioModel


class UIRenderer:
    """Handles all UI rendering for the Dojo application"""
    
    def __init__(self, renderer, game_state: DojoState):
        self.renderer = renderer
        self.game_state = game_state
    
    def render_main_ui(self):
        """Render the main UI elements (score, time, etc.)"""
        if self.game_state.game_phase in [ScenarioPhase.MENU, *CUSTOM_MODES]:
            return

        # Draw initial UI while components are initializing.
        # Especially HotkeyManager / Pygame can randomly take longer to initialize while blocking the main thread.
        if not self.game_state.dojo_components_initialized:
            header_text = "Welcome to the Dojo."
            self.renderer.draw_string_2d(header_text, 20, 50, 1, self.renderer.yellow)
            warning_text = ("Waiting for components to initialize... "
                            "\nShould take a few seconds. "
                            "\nIf not, try waiting for up to a minute or restarting your PC.")
            self.renderer.draw_string_2d(
                warning_text, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 10, 1, self.renderer.yellow
            )
            return

        minutes, seconds = self.game_state.get_time_since_start()
        seconds_str = f"{seconds:02d}"
        
        # Prepare text content
        text = "Welcome to the Dojo. Press 'm' to enter menu."
        previous_record = "No record"
        
        if self.game_state.gym_mode == GymMode.SCENARIO:
            scores = f"Human: {self.game_state.human_score} Bot: {self.game_state.bot_score}"
            total_score = f"Total: {self.game_state.human_score + self.game_state.bot_score}"
            time_since_start = f"Time: {minutes}:{seconds_str}"
            timeout_enabled = f"Timeouts enabled: {self.game_state.enable_timeouts}"
            freeze_scenario_enabled = f"Scenario frozen: {self.game_state.freeze_scenario}"
            offensive_mode_name = f"Offensive Mode: {self.game_state.offensive_mode.name}"
            defensive_mode_name = f"Defensive Mode: {self.game_state.defensive_mode.name}"
            player_role_name = "offense" if self.game_state.human_offense else "defense"
            player_role_string = f"Player Role: {player_role_name}"
            previous_record = ""
            game_phase_name = f"Game Phase: {self.game_state.game_phase.name}"
        elif self.game_state.gym_mode == GymMode.RACE:
            scores = f"Completed: {self.game_state.human_score}"
            total_score = f"Out of: {self.game_state.num_trials}"
            time_since_start = f"Time: {minutes}:{seconds_str}"
            previous_record_data = self.game_state.get_previous_record()
            if previous_record_data:
                prev_minutes = int(previous_record_data // 60)
                prev_seconds = int(previous_record_data % 60)
                previous_record = f"Previous Record: {prev_minutes}:{prev_seconds:02d}"
        
        # === Render UI elements
        # Main instruction text
        self.renderer.draw_string_2d(text, 20, 50, 1, self.renderer.yellow)
        
        # Score box content
        self.renderer.draw_string_2d(
            scores, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 10,
            1, self.renderer.white
        )
        self.renderer.draw_string_2d(
            total_score, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 40,
            1, self.renderer.white
        )
        self.renderer.draw_string_2d(
            time_since_start, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 70,
            1, self.renderer.white
        )
        self.renderer.draw_string_2d(
            previous_record, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 100,
            1, self.renderer.white
        )
        if self.game_state.gym_mode == GymMode.SCENARIO:
            self.renderer.draw_string_2d(
                offensive_mode_name, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 130,
                1, self.renderer.white
            )
            self.renderer.draw_string_2d(
                defensive_mode_name, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 160,
                1, self.renderer.white
            )
            self.renderer.draw_string_2d(
                player_role_string, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 190,
                1, self.renderer.white
            )
            self.renderer.draw_string_2d(
                game_phase_name, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 220,
                1, self.renderer.white
            )
            self.renderer.draw_string_2d(
                timeout_enabled, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 250,
                1, self.renderer.white
            )
            self.renderer.draw_string_2d(
                freeze_scenario_enabled, SCORE_BOX_START_X + 10, SCORE_BOX_START_Y + 280,
                1, self.renderer.white
            )

    
    def render_velocity_vectors(self, scenario: ScenarioModel):
        """Render velocity vectors for all objects in custom mode"""

        physics = [
            scenario.offensive_car_state.physics,
            scenario.defensive_car_state.physics,
            scenario.ball_state.physics,
        ]

        for phys in physics:
            self.renderer.draw_line_3d(phys.location, phys.location + phys.velocity, self.renderer.white)
