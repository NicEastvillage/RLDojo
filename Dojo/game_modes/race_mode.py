import numpy as np
import time
from rlbot.flat import DesiredGameState, DesiredBallState, DesiredCarState, DesiredPhysics, Vector3Partial, RotatorPartial

import utils
from .base_mode import BaseGameMode
from dojo_state import RacePhase, CarIndex
from race_record import RaceRecord, RaceRecords, store_race_records


class RaceMode(BaseGameMode):
    """Handles race-based training mode"""
    
    def __init__(self, game_state, game_interface):
        super().__init__(game_state, game_interface)
        self.race = None
        self.bot_car_desired_state = None
        self.ball_desired_state = None
        self.human_freeze_desired_state = None
        self.last_menu_phase_time = 0
    
    def initialize(self):
        """Initialize race mode"""
        np.random.seed(0)
        self.game_state.human_score = 0
        self.game_state.bot_score = 0
        self.game_state.started_time = self.game_state.cur_time
        self.game_state.game_phase = RacePhase.SETUP

        # Spawn the player car in the middle of the map
        player_car_state = DesiredCarState(
            physics=DesiredPhysics(
                location=Vector3Partial(0, 0, 18),
                velocity=Vector3Partial(0, 0, 0),
                rotation=RotatorPartial(0, 0, 0),
                angular_velocity=Vector3Partial(0, 0, 0),
            ),
            boost_amount=33,
        )
        
        # Tuck the bot above the map
        self.bot_car_desired_state = DesiredCarState(
            physics=DesiredPhysics(
                location=Vector3Partial(0, 0, 2500),
                velocity=Vector3Partial(0, 0, 0),
                rotation=RotatorPartial(0, 0, 0),
                angular_velocity=Vector3Partial(0, 0, 0),
            )
        )

        car_states = [self.bot_car_desired_state, player_car_state]

        self.game_interface.send_msg(DesiredGameState(car_states=car_states))

    def pick_new_ball_state(self):
        self.ball_desired_state = None

        # Place the ball in a random location
        x, y, z = 10_000, 10_000, 10_000
        while abs(x) > utils.SIDE_WALL - utils.BALL_RADIUS or abs(y) > utils.BACK_WALL - utils.BALL_RADIUS or abs(x) + abs(y) > utils.DIAG_WALL - 2 * utils.BALL_RADIUS:
            x = utils.random_between(-(utils.SIDE_WALL - 200), utils.SIDE_WALL - 200)
            y = utils.random_between(-(utils.BACK_WALL - 200), utils.BACK_WALL - 200)
        z = utils.random_between(utils.BALL_RADIUS, utils.CEILING - 1000)
        ball_velocity = Vector3Partial(0, 0, 0)

        self.ball_desired_state = DesiredBallState(DesiredPhysics(location=Vector3Partial(x, y, z), velocity=ball_velocity))

    def cleanup(self):
        """Clean up race mode resources"""
        self.race = None
    
    def update(self, packet):
        """Update race mode based on current game phase"""
        if self.game_state.paused:
            return
            
        phase_handlers = {
            RacePhase.INIT: self._handle_init_phase,
            RacePhase.SETUP: self._handle_setup_phase,
            RacePhase.ACTIVE: self._handle_active_phase,
            RacePhase.MENU: self._handle_menu_phase,
            RacePhase.EXITING_MENU: self._handle_menu_exiting_phase,
            RacePhase.FINISHED: self._handle_finished_phase,
        }
        
        handler = phase_handlers.get(self.game_state.game_phase)
        if handler:
            handler(packet)
    
    def _handle_init_phase(self, packet):
        """Handle initialization phase"""
        self.initialize()
    
    def _handle_setup_phase(self, packet):
        """Handle setup phase"""
        self.pick_new_ball_state()
        self.apply_state_setting(packet)
        self.game_state.game_phase = RacePhase.ACTIVE
    
    def _handle_active_phase(self, packet):
        """Handle active race phase"""
        # Check if the current ball location has moved significantly
        if self._ball_moved_significantly(packet):
            self.game_state.human_score += 1
            self.game_state.game_phase = RacePhase.SETUP
            
            if self.game_state.human_score >= self.game_state.num_trials:
                self.game_state.game_phase = RacePhase.FINISHED
                return
        
        # Continue setting the ball location to the race ball location
        self.apply_state_setting(packet)
    
    def _handle_menu_phase(self, packet):
        """Handle menu phase"""
        if self.human_freeze_desired_state is None:
            human_phys = packet.players[-1].physics
            self.human_freeze_desired_state = DesiredCarState(
                physics=DesiredPhysics(
                    location=Vector3Partial(human_phys.location.x, human_phys.location.y, human_phys.location.z),
                    velocity=Vector3Partial(human_phys.velocity.x, human_phys.velocity.y, human_phys.velocity.z),
                    rotation=RotatorPartial(human_phys.rotation.pitch, human_phys.rotation.yaw,
                                            human_phys.rotation.roll),
                    angular_velocity=Vector3Partial(human_phys.angular_velocity.x, human_phys.angular_velocity.y,
                                                    human_phys.angular_velocity.z),
                ),
                boost_amount=packet.players[-1].boost,
            )

        self.apply_state_setting(packet)
        self.last_menu_phase_time = time.time()
        
    def _handle_menu_exiting_phase(self, packet):
        """Unfreeze game state after a 3 second countdown"""
        # For each second, render a countdown from 3 to 1
        if time.time() - self.last_menu_phase_time > 3:
            self.human_freeze_desired_state = None
            self.game_state.game_phase = RacePhase.ACTIVE
        else:
            self.game_interface.renderer.draw_string_2d(str(3 - int(time.time() - self.last_menu_phase_time)), 850, 200, 15, self.game_interface.renderer.white)
        self.apply_state_setting(packet)
    
    def _handle_finished_phase(self, packet):
        """Handle finished phase - save records and restart"""
        self.apply_state_setting(packet)
        
        # Save the record
        if self.game_state.human_score >= self.game_state.num_trials:
            total_time = self.game_state.cur_time - self.game_state.started_time
            print(f"Race completed in {total_time} seconds")
            
            record = RaceRecord(
                number_of_trials=self.game_state.num_trials,
                time_to_finish=float(total_time)
            )
            self.game_state.race_mode_records.set_record(record)
            store_race_records(self.game_state.race_mode_records)
        
        time.sleep(10)
        self.game_state.game_phase = RacePhase.INIT
    
    def _ball_moved_significantly(self, packet) -> bool:
        """Check if the ball has moved significantly from its target position"""

        target_pos = self.ball_desired_state.physics.location
        current_pos = packet.balls[0].physics.location
        
        return (abs(target_pos.x - current_pos.x) > 2 or
                abs(target_pos.y - current_pos.y) > 2 or
                abs(target_pos.z - current_pos.z) > 2)
    
    def apply_state_setting(self, packet):
        """Update the game state with bot car position and race ball position"""

        # Human is always at last index, so we only need a single-item list of cars unless we want to freeze the player
        car_states = [self.bot_car_desired_state]
        if self.game_state.game_phase in [RacePhase.MENU, RacePhase.EXITING_MENU]:
            car_states.append(self.human_freeze_desired_state)

        state = DesiredGameState(car_states=car_states, ball_states=[self.ball_desired_state])
        self.game_interface.send_msg(state)
