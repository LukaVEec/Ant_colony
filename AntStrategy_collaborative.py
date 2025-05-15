import random
from ant import AntStrategy
from common import AntPerception, AntAction, TerrainType


class CollabStrategy(AntStrategy):



    def __init__(self):
        # Track the last action to alternate between movement and pheromone deposit
        self.ants_last_action = {}  # ant_id -> (AntAction) last_action
        self.ants_turns = {}  # ant_id -> (int) number of consecutive turns


    def decide_action(self, perception: AntPerception) -> AntAction:

        # Get ant's ID to track its actions
        ant_id = perception.ant_id
        last_action = self.ants_last_action.get(ant_id, None)

        # Ant carries no food : search food

        if not perception.has_food:
            # Pick up food if standing on it
            if ((0, 0) in perception.visible_cells # theoretically always true
                and perception.visible_cells[(0, 0)] == TerrainType.FOOD
            ):
                self.ants_last_action[ant_id] = AntAction.PICK_UP_FOOD
                self.ants_turns[ant_id] = 0
                return AntAction.PICK_UP_FOOD

        # Ant carries food : search colony

        elif perception.has_food:
            # Drop food if at colony and carrying food
            if ((0, 0) in perception.visible_cells  # theoretically always true
                and perception.visible_cells[(0, 0)] == TerrainType.COLONY
            ):
                self.ants_last_action[ant_id] = AntAction.DROP_FOOD
                self.ants_turns[ant_id] = 0
                return AntAction.DROP_FOOD

        # Alternate between movement and dropping pheromones
        # If last action was not a pheromone drop, drop pheromone

        if last_action not in [AntAction.DEPOSIT_HOME_PHEROMONE, AntAction.DEPOSIT_FOOD_PHEROMONE]:
            if perception.has_food:
                self.ants_last_action[ant_id] = AntAction.DEPOSIT_FOOD_PHEROMONE
                return AntAction.DEPOSIT_FOOD_PHEROMONE
            else:
                self.ants_last_action[ant_id] = AntAction.DEPOSIT_HOME_PHEROMONE
                return AntAction.DEPOSIT_HOME_PHEROMONE

        # Otherwise, perform movement
        action = self.decide_movement(perception)
        self.ants_last_action[ant_id] = action
        return action

    def decide_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        ant_dir = perception.direction.value
        ant_id = perception.ant_id

        if not perception.has_food : # Ant carries no food : search food

            # Priority F.1 : Ant can see food so moves towards it
            if perception.can_see_food():
                best_dir = perception.get_food_direction()  # 0 p.ex. (NORTH)
                if best_dir is not None:
                    return self.decide_turn(perception, best_dir, ant_dir)

            # Priority F.2 : Ant detects food pheromone so follows strongest direction
            return self.follow_pheromone(perception, perception.food_pheromone)

        else: # Ant carries food : search colony

            # Priority C.1 : Ant can see colony so move towards colony
            if perception.can_see_colony():
                best_dir = perception.get_colony_direction()
                if best_dir is not None:
                    return self.decide_turn(perception, best_dir, ant_dir)

            # Priority C.2 : Ant detects home pheromone so follows strongest direction
            return self.follow_pheromone(perception, perception.home_pheromone)


    def follow_pheromone(self, perception : AntPerception, ph_type : dict) -> AntAction:
        """Follow pheromones if detected. Do a random movement if not."""

        if not ph_type : # no useful pheromone detected
            return self.decide_random_movement(perception)

        if perception.ant_id not in self.ants_turns:
            self.ants_turns[perception.ant_id] = 0

        if self.ants_turns[perception.ant_id] > 4 : # prevent too much consecutive turns
            self.ants_turns[perception.ant_id] = 0
            return AntAction.MOVE_FORWARD if self.valid_move(perception) else self.decide_random_movement(perception)

        ant_dir = perception.direction.value
        max_x, max_y = 0, 0
        max_level = 0
        for (x, y), ph_level in ph_type.items():
            if ph_level != 0 :
                if ph_level > max_level:
                    max_level = ph_level
                    max_x, max_y = x, y

        if max_level == 0:
            # Random movement if no pheromone detected
            return self.decide_random_movement(perception)


        ph_dir = perception._get_direction_from_delta(max_x, max_y)
        return self.decide_turn(perception, ph_dir, ant_dir)


    def decide_random_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        ant_id = perception.ant_id
        movement_choice = random.random()

        if perception.steps_taken < 100 :
            forward = 0.9
            turn = 0.95
        else :
            forward = 0.7 # 70% chance to move forward
            turn = 0.85 # 15% chance to turn left or right

        if self.valid_move(perception) and movement_choice < forward :
                self.ants_turns[ant_id] = 0
                return AntAction.MOVE_FORWARD
        elif movement_choice < turn:
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 0
            self.ants_turns[ant_id] += 1
            return AntAction.TURN_LEFT
        else:
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 0
            self.ants_turns[ant_id] += 1
            return AntAction.TURN_RIGHT

    def decide_turn(self, perception : AntPerception, dir_a : int, dir_b : int) -> AntAction:
        """ Decide to go forward or to turn"""

        ant_id = perception.ant_id
        diff = (dir_a - dir_b) % 8

        randomizer = random.random()
        if perception.steps_taken > 250 and randomizer < 0.1:  # 10% chance to take a random décision
            return self.decide_random_movement(perception)

        if self.valid_move(perception) and diff == 0:
                self.ants_turns[ant_id] = 0
                return AntAction.MOVE_FORWARD
        elif 1 <= diff <= 3:
            if ant_id not in self.ants_turns:  # initialize consecutive turns if necessary
                self.ants_turns[ant_id] = 0
            self.ants_turns[ant_id] += 1
            return AntAction.TURN_RIGHT
        elif 5 <= diff <= 7:
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 0
            self.ants_turns[ant_id] += 1
            return AntAction.TURN_LEFT
        else: # U-turn, go left or right
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 0
            self.ants_turns[ant_id] += 1
            return random.choice([AntAction.TURN_LEFT, AntAction.TURN_RIGHT])


    def valid_move(self, perception: AntPerception) -> bool:
        """
        Check if the move is valid
        """
        if perception.direction.value == 0:
            if (0, -1) in perception.visible_cells and perception.visible_cells[(0, -1)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 1:
            if (1, -1) in perception.visible_cells and perception.visible_cells[(1, -1)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 2:
            if (1, 0) in perception.visible_cells and perception.visible_cells[(1, 0)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 3:
            if (1, 1) in perception.visible_cells and perception.visible_cells[(1, 1)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 4:
            if (0, 1) in perception.visible_cells and perception.visible_cells[(0, 1)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 5:
            if (-1, 1) in perception.visible_cells and perception.visible_cells[(-1, 1)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 6:
            if (-1, 0) in perception.visible_cells and perception.visible_cells[(-1, 0)] != TerrainType.WALL:
                return True
        elif perception.direction.value == 7:
            if (-1, -1) in perception.visible_cells and perception.visible_cells[(-1, -1)] != TerrainType.WALL:
                return True
        return False