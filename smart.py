import random
from ant import AntStrategy
from common import AntPerception, AntAction, TerrainType, Direction

"""
Potentielles améliorations : 
    - retenir où se trouve la colonie pour y retourner le plus vite possible
    - faire quelques mouvements random après capture de nourriture pour répandre phéromones ?
    - utilisation de ants_nearby ?
    - amélioration de la détection de phéromones


"""

class CollabStrategy(AntStrategy):



    def __init__(self):
        # Track the last action to alternate between movement and pheromone deposit
        self.ants_last_action = {}  # ant_id -> (AntAction) last_action
        self.ants_turns = {}  # ant_id -> (int) number of consecutive turns
        self.colony_position = {}  # ant_id -> (x,y) tuple of colony position
        self.current_position = {} # ant_id -> (x,y) tuple of ant position
        self.walls = {} # ant_id -> true if ant faced a wall, so use pheromones to go home


    def decide_action(self, perception: AntPerception) -> AntAction:

        # Get ant's ID to track its actions
        ant_id = perception.ant_id
        last_action = self.ants_last_action.get(ant_id, None)


        # Initialize current position, colony position and walls attribute
        if ant_id not in self.current_position:
            self.current_position[ant_id] = (0, 0)

        if ant_id not in self.colony_position and perception.visible_cells.get((0, 0)) == TerrainType.COLONY:
            self.colony_position[ant_id] = self.current_position[ant_id]

        if ant_id not in self.walls :
            self.walls[ant_id] = False

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

            # Priority C.2 : Ant knows colony position so move towards colony
            if self.colony_position[ant_id] is not None and not self.walls[ant_id] :
                return self.go_home(perception)

            # Priority C.3 : Ant detects home pheromone so follows strongest direction
            return self.follow_pheromone(perception, perception.home_pheromone)

    def go_home(self, perception: AntPerception) -> AntAction:
        """ Go home by using coordinates of colony"""
        if perception.ant_id not in self.ants_turns:
            self.ants_turns[perception.ant_id] = 0

        if self.ants_turns[perception.ant_id] > 4 : # prevent too much consecutive turns
            self.ants_turns[perception.ant_id] = 0
            self.update_position(perception)
            return AntAction.MOVE_FORWARD if self.valid_move(perception) else self.decide_random_movement(perception)

        ant_dir = perception.direction.value
        dx = self.colony_position[perception.ant_id][0] - self.current_position[perception.ant_id][0]
        dy = self.colony_position[perception.ant_id][1] - self.current_position[perception.ant_id][1]
        home_dir = perception._get_direction_from_delta(dx, dy)

        return self.decide_turn(perception, home_dir, ant_dir)


    def follow_pheromone(self, perception : AntPerception, ph_type : dict) -> AntAction:
        """Follow pheromones if detected. Do a random movement if not."""

        if not ph_type : # no useful pheromone detected
            return self.decide_random_movement(perception)

        if perception.ant_id not in self.ants_turns:
            self.ants_turns[perception.ant_id] = 0

        if self.ants_turns[perception.ant_id] > 4 : # prevent too much consecutive turns
            self.ants_turns[perception.ant_id] = 0
            self.update_position(perception)
            return AntAction.MOVE_FORWARD if self.valid_move(perception) else self.decide_random_movement(perception)

        ant_dir = perception.direction.value

        max_value = 0.0
        best_dir = 0
        for direction in Direction:  # on itère sur toutes les cases voisines de la fourmi
            dx, dy = Direction.get_delta(direction) # p.ex (1,0) pour East
            value_sum = 0.0

            for strength in range(1, 4):
                check_x, check_y = 0 + dx * strength, 0 + dy * strength  # (1, 0), (2,0) et (3,0) pour East
                ph_level = ph_type.get((check_x, check_y), 0.0)
                value_sum += ph_level / strength

            if value_sum > max_value:
                max_value = value_sum
                best_dir = direction.value

        if max_value == 0 : # aucune phéromone captée
            return self.decide_random_movement(perception)

        return self.decide_turn(perception, best_dir, ant_dir)

    def follow_pheromone2(self, perception : AntPerception, ph_type : dict) -> AntAction:
        """Follow pheromones if detected. Do a random movement if not."""

        if not ph_type : # no useful pheromone detected
            return self.decide_random_movement(perception)

        if perception.ant_id not in self.ants_turns:
            self.ants_turns[perception.ant_id] = 0

        if self.ants_turns[perception.ant_id] > 4 : # prevent too much consecutive turns
            self.ants_turns[perception.ant_id] = 0
            return AntAction.MOVE_FORWARD if self.valid_move(perception) else self.decide_random_movement(perception)

        ant_dir = perception.direction.value

        if ph_type == perception.home_pheromone:

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

            """max_value = 0.0
            best_dir = 0
            for direction in Direction:  # on itère sur toutes les cases voisines de la fourmi
                dx, dy = Direction.get_delta(direction)  # p.ex (1,0) pour East
                value_sum = 0.0

                check_x, check_y = 0 + dx , 0 + dy
                ph_level = ph_type.get((check_x, check_y), 0.0)
                value_sum += ph_level

                if value_sum > max_value:
                    max_value = value_sum
                    best_dir = direction.value

            if max_value == 0:  # aucune phéromone captée
                return self.decide_random_movement(perception)

            return self.decide_turn(perception, best_dir, ant_dir)"""

        else :

            max_value = 0.0
            best_dir = 0
            for direction in Direction:  # on itère sur toutes les cases voisines de la fourmi
                dx, dy = Direction.get_delta(direction) # p.ex (1,0) pour East
                value_sum = 0.0

                for strength in range(1, 4):
                    check_x, check_y = 0 + dx * strength, 0 + dy * strength  # (1, 0), (2,0) et (3,0) pour East
                    ph_level = ph_type.get((check_x, check_y), 0.0)
                    value_sum += ph_level / strength

                if value_sum > max_value:
                    max_value = value_sum
                    best_dir = direction.value

            if max_value == 0 : # aucune phéromone captée
                return self.decide_random_movement(perception)

            return self.decide_turn(perception, best_dir, ant_dir)


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
                self.update_position(perception)
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

        if diff == 0 :
            if self.valid_move(perception):
                self.ants_turns[ant_id] = 0
                self.update_position(perception)
                return AntAction.MOVE_FORWARD
            else :
                self.walls[ant_id] = True # Wall


        if 1 <= diff <= 3:
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

    def update_position(self, perception : AntPerception):
        """
        Update coordinates of the ant after moving in a given direction
        """
        if perception.ant_id not in self.current_position:
            self.current_position[perception.ant_id] = (0, 0)

        dir = perception.direction.value
        x_ant = self.current_position[perception.ant_id][0]
        y_ant = self.current_position[perception.ant_id][1]

        if dir == 0 :
            self.current_position[perception.ant_id] = (x_ant, y_ant - 1)
        elif dir == 1 :
            self.current_position[perception.ant_id] = (x_ant + 1, y_ant - 1)
        elif dir == 2 :
            self.current_position[perception.ant_id] = (x_ant + 1, y_ant)
        elif dir == 3 :
            self.current_position[perception.ant_id] = (x_ant + 1, y_ant + 1)
        elif dir == 4 :
            self.current_position[perception.ant_id] = (x_ant, y_ant + 1)
        elif dir == 5 :
            self.current_position[perception.ant_id] = (x_ant - 1, y_ant + 1)
        elif dir == 6 :
            self.current_position[perception.ant_id] = (x_ant - 1, y_ant)
        elif dir == 7 :
            self.current_position[perception.ant_id] = (x_ant - 1, y_ant - 1)

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