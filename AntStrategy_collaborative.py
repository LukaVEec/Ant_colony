import random
from typing import Optional

import ant
import environment
from ant import AntStrategy, Ant
from common import AntPerception, AntAction, TerrainType, Direction
from environment import PheromoneMap, Environment
#from non_collaborative import check_move


class CollabStrategy(AntStrategy):



    def __init__(self):
        # Track the last action to alternate between movement and pheromone deposit
        self.ants_last_action = {}  # ant_id -> (AntAction) last_action
        self.ants_turns = {}  # ant_id -> (int) +1 if ant turned. initialize to 0 if MOVE_FORWARD
        self.x = {}
        self.y = {} ## essayer avec des dictionnaires ant_id -> (x,y) les coordonées globaux


    def decide_action(self, perception: AntPerception) -> AntAction:

        # Get ant's ID to track its actions
        ant_id = perception.ant_id
        if ant_id not in self.x and ant_id not in self.y:
            self.x[ant_id] = 0
            self.y[ant_id] = 0
        last_action = self.ants_last_action.get(ant_id, None) # ne pas oublier de le mettre à jour !!!

        # Ant carries no food : search food

        if not perception.has_food:
            # Pick up food if standing on it
            if ((0, 0) in perception.visible_cells # théoriquement toujours vrai
                and perception.visible_cells[(0, 0)] == TerrainType.FOOD
            ):
                self.ants_last_action[ant_id] = AntAction.PICK_UP_FOOD
                return AntAction.PICK_UP_FOOD

        # Ant carries food : search colony

        elif perception.has_food:
            # Drop food if at colony and carrying food
            if ((0, 0) in perception.visible_cells  # théoriquement toujours vrai
                    and perception.visible_cells[(0, 0)] == TerrainType.COLONY
            ):
                self.ants_last_action[ant_id] = AntAction.DROP_FOOD
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

        # Otherwise, perform movement (pour l'instant, random)
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
                for (dx, dy), terrain in perception.visible_cells.items():
                    if terrain == TerrainType.FOOD:
                        if dy > 0 and self.valid_move(perception):  # Food is ahead in some direction
                            self.ants_turns[ant_id] = 0
                            if ant_id not in self.x and ant_id not in self.y:
                                self.x[ant_id] = 0
                                self.y[ant_id] = 0
                            self.update_position(perception)
                            return AntAction.MOVE_FORWARD

                best_dir = perception.get_food_direction()  # 0 p.ex. (NORTH)
                if best_dir != None:
                    return self.decide_turn(perception, best_dir, ant_dir)

            # Priority F.2 : Ant detects food pheromone so follows strongest direction
            return self.follow_pheromone(perception, perception.food_pheromone)

        # Ant carries food : search colony
        else:

            # Priority C.1 : Ant can see colony so move towards colony
            if perception.can_see_colony():
                for (dx, dy), terrain in perception.visible_cells.items():
                    if terrain == TerrainType.COLONY:
                        if dy > 0 and self.valid_move(perception):
                            self.ants_turns[ant_id] = 0
                            self.update_position(perception)
                            return AntAction.MOVE_FORWARD

                best_dir = perception.get_colony_direction()
                if best_dir != None :
                    return self.decide_turn(perception, best_dir, ant_dir)

            # Priority C.2 : Ant detects home pheromone so follows strongest direction
            return self.follow_pheromone(perception, perception.home_pheromone)

        # Random movement if no other choice



    def follow_pheromone(self, perception : AntPerception, ph_type : dict) -> AntAction:
        """Follow pheromones if detected. Do a random movement if not."""

        ### FOURMIS restent bloquées à cause d'une équivalence de

        if not ph_type :
            return self.decide_random_movement(perception)

        if perception.ant_id not in self.ants_turns:
            self.ants_turns[perception.ant_id] = 0

        if self.ants_turns[perception.ant_id] > 2 :
            return AntAction.MOVE_FORWARD if self.valid_move(perception) else self.decide_random_movement(perception)

        ant_dir = perception.direction.value
        x_ant = self.x[perception.ant_id]
        y_ant = self.y[perception.ant_id]

        max_value = 0.0
        best_dir = 0


        """
        max_x, max_y = 0, 0
        max_level = 0
        for (x, y), ph_level in ph_type.items():
            if ph_level != None :
                if ph_level > max_level:
                    max_level = ph_level
                    max_x, max_y = x, y

        if max_level == 0:
            # Random movement if no pheromone detected
            return self.decide_random_movement(perception)
        """

        randomizer = random.random()  # pour empêcher de rester bloqué trop longtemps

        for direction in Direction:  # on itère sur toutes les cases voisines de la fourmi
            dx, dy = Direction.get_delta(direction) # p.ex (1,0) pour East
            value_sum = 0.0

            for strength in range(1, 4):
                check_x, check_y = x_ant + dx * strength, y_ant + dy * strength  # (1, 0), (2,0) et (3,0) pour East
                if 0 <= check_x <= 35 and 0 <= check_y <= 35:
                    value_sum += ph_type.get((check_x, check_y), 0.0)

            if value_sum > max_value:
                max_value = value_sum
                best_dir = direction.value

        if max_value == 0 : # aucune phéromone captée
            return self.decide_random_movement(perception)

        ## S'active lorsqu'on atteint un certain stade
        if perception.steps_taken > 250 and randomizer < 0.15:  #15% de chances de prendre une décision random
            return self.decide_random_movement(perception)

        ## S'active lorsque trop de fourmis sont collées les unes aux autres # Ne fonctionne pas très bien
        #if (len(perception.nearby_ants) > 10 and randomizer < 0.5
                #and perception.steps_taken > 150 and perception.has_food):
            #return self.decide_random_movement(perception)

        #ph_dir = perception._get_direction_from_delta(max_x, max_y)
        #return self.decide_turn(perception, ph_dir, ant_dir)
        return self.decide_turn(perception, best_dir, ant_dir)


    def decide_random_movement(self, perception: AntPerception) -> AntAction:
        """Decide which direction to move based on current state"""

        ant_id = perception.ant_id

        # Random movement if no specific goal
        movement_choice = random.random()
        pct = 0.70 # 85% chance to move forward
        turn = 0.85 # 15% chance to turn left or right

        if perception.steps_taken < 100 : # autres pourcentages avant
            pct = 0.92
            turn = 0.96

        if self.valid_move(perception) and movement_choice < pct :
                self.ants_turns[ant_id] = 0
                self.update_position(perception)
                return AntAction.MOVE_FORWARD
        elif movement_choice < turn:
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 1
            else :
                self.ants_turns[ant_id] += 1
            return AntAction.TURN_LEFT
        else:
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 1
            else:
                self.ants_turns[ant_id] += 1
            return AntAction.TURN_RIGHT

    def decide_turn(self, perception : AntPerception, dirA : int, dirB : int) -> AntAction:
        """ Decide to go forward or to turn"""

        ant_id = perception.ant_id

        if self.valid_move(perception) and  (dirA == dirB):
                self.ants_turns[ant_id] = 0
                self.update_position(perception)
                return AntAction.MOVE_FORWARD
        elif (dirA > dirB and dirA > 0) or (dirA < dirB and dirA == 0):
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 1
            else:
                self.ants_turns[ant_id] += 1
            return AntAction.TURN_RIGHT
        else:
            if ant_id not in self.ants_turns:
                self.ants_turns[ant_id] = 1
            else:
                self.ants_turns[ant_id] += 1
            return AntAction.TURN_LEFT


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

    def update_position(self, perception: AntPerception):
        if perception.direction.value == 0:
            self.y[perception.ant_id] -= 1
        elif perception.direction.value == 1:
            self.y[perception.ant_id] -= 1
            self.x[perception.ant_id] += 1
        elif perception.direction.value == 2:
            self.x[perception.ant_id] += 1
        elif perception.direction.value == 3:
            self.x[perception.ant_id] += 1
            self.y[perception.ant_id] += 1
        elif perception.direction.value == 4:
            self.y[perception.ant_id] += 1
        elif perception.direction.value == 5:
            self.x[perception.ant_id] -= 1
            self.y[perception.ant_id] += 1
        elif perception.direction.value == 6:
            self.x[perception.ant_id] -= 1
        elif perception.direction.value == 7:
            self.x[perception.ant_id] -= 1
            self.y[perception.ant_id] -= 1



