import random
from environment import TerrainType, AntPerception
from ant import AntAction, AntStrategy


class FirstStrategy(AntStrategy):
    """
    A simple strategy for ants. When an ant perceives food in its visible cells, it finds the shortest path to it.
    If the ant is carrying food, it will find the shortest path to the colony.
    """

    def __init__(self):
        """Initialize the strategy with last action tracking"""
        self.ants_last_action = {}  # ant_id -> last_action
        self.food_positions = {}  # List to store food positions
        self.colony_position = {}  # List to store colony positions
        self.current_position = {}
        self.old_positions = {}  # List to store old positions
        
    def decide_action(self, perception: AntPerception) -> AntAction:
        """Decide an action based on current perception"""
        

        ant_id = perception.ant_id
        last_action = self.ants_last_action.get(ant_id, None)
        if ant_id not in self.current_position:
            self.current_position[ant_id] = (0, 0)
        if ant_id in self.food_positions and len(self.food_positions[ant_id]) != 0:
            if(self.current_position[ant_id] == self.food_positions[ant_id][0]) and perception.visible_cells.get((0,0)) != TerrainType.FOOD:
                self.food_positions[ant_id].remove(self.current_position[ant_id])
        if last_action == AntAction.PICK_UP_FOOD and perception.visible_cells.get((0, 0)) != TerrainType.FOOD and self.current_position[ant_id] in self.food_positions[ant_id]:
            self.food_positions[ant_id].remove(self.current_position[ant_id])



        # If the ant is at the colony, store its position
        if ant_id not in self.colony_position and perception.visible_cells.get((0, 0)) == TerrainType.COLONY:
            self.colony_position[ant_id] = self.current_position[ant_id]

        # Priority 1: Pick up food if standing on it
        if (
            not perception.has_food
            and (0, 0) in perception.visible_cells
            and perception.visible_cells[(0, 0)] == TerrainType.FOOD
        ):
            self.ants_last_action[ant_id] = AntAction.PICK_UP_FOOD
            if self.current_position[ant_id] not in self.food_positions:
                if ant_id not in self.food_positions:
                    self.food_positions[ant_id] = [self.current_position[ant_id]]
                else:
                    self.food_positions[ant_id].append(self.current_position[ant_id]) 
            return AntAction.PICK_UP_FOOD

        # Priority 2: Drop food if at colony and carrying food
        if (
            perception.has_food
            and TerrainType.COLONY in perception.visible_cells.values()
        ):
            for pos, terrain in perception.visible_cells.items():
                if terrain == TerrainType.COLONY:
                    if pos == (0, 0):  # Directly on colony
                        self.ants_last_action[ant_id] = AntAction.DROP_FOOD
                        return AntAction.DROP_FOOD


        # Priority 3: If can see colony, move toward it to store the position
        if perception.can_see_colony and ant_id not in self.colony_position:
            best_direction = perception.get_colony_direction()
            if best_direction is not None:
                if best_direction != perception.direction.value or check_move(perception) == False:
                    action = self._decide_movement(perception, ant_id)
                    self.ants_last_action[ant_id] = action
                    return action
                else:
                    self.ants_last_action[ant_id] = AntAction.MOVE_FORWARD
                    self.current_position[ant_id] = move(perception.direction.value, self.current_position[ant_id][0], self.current_position[ant_id][1])
                    return AntAction.MOVE_FORWARD
        
        
        
        # Priority 4A : If the ant has no food and can see food, try to move toward it
        if (not perception.has_food):
            if perception.can_see_food():
                best_direction = perception.get_food_direction()
                if best_direction is not None:
                    if best_direction != perception.direction.value or check_move(perception) == False:
                        action = self._decide_movement(perception, ant_id)
                        self.ants_last_action[ant_id] = action
                        return action
                    else:
                        self.ants_last_action[ant_id] = AntAction.MOVE_FORWARD
                        self.current_position[ant_id] = move(perception.direction.value, self.current_position[ant_id][0], self.current_position[ant_id][1])
                        return AntAction.MOVE_FORWARD
            else:
                if ant_id in self.food_positions and len(self.food_positions[ant_id]) != 0:
                    best_direction = get_direction(self.current_position[ant_id][0], self.current_position[ant_id][1], self.food_positions[ant_id][0][0], self.food_positions[ant_id][0][1])
                    if best_direction is not None:
                        if best_direction != perception.direction.value or check_move(perception) == False:
                            action = self._decide_movement(perception, ant_id)
                            self.ants_last_action[ant_id] = action
                            return action
                        else:
                            self.ants_last_action[ant_id] = AntAction.MOVE_FORWARD
                            self.current_position[ant_id] = move(perception.direction.value, self.current_position[ant_id][0], self.current_position[ant_id][1])
                            return AntAction.MOVE_FORWARD
                

        # Priority 4B: If the ant has food and can see the colony, try to move toward it
        action = None
        if perception.has_food:
            if perception.can_see_colony():
                best_direction = perception.get_colony_direction()
                if best_direction is not None:
                    if best_direction != perception.direction.value or check_move(perception) == False:
                        action = self._decide_movement(perception, ant_id)
                        self.ants_last_action[ant_id] = action
                        
                    else:
                        self.ants_last_action[ant_id] = AntAction.MOVE_FORWARD
                        self.current_position[ant_id] = move(perception.direction.value, self.current_position[ant_id][0], self.current_position[ant_id][1])
                        return AntAction.MOVE_FORWARD
            else:
                if ant_id in self.colony_position:
                    best_direction = get_direction(self.current_position[ant_id][0], self.current_position[ant_id][1], self.colony_position[ant_id][0], self.colony_position[ant_id][1])
                    if best_direction is not None:
                        if best_direction != perception.direction.value or check_move(perception) == False:
                            action = self._decide_movement(perception, ant_id)
                            self.ants_last_action[ant_id] = action
                            return action
                           
                        else:
                            self.ants_last_action[ant_id] = AntAction.MOVE_FORWARD
                            self.current_position[ant_id] = move(perception.direction.value, self.current_position[ant_id][0], self.current_position[ant_id][1])
                            action = AntAction.MOVE_FORWARD
                            return action

        # Otherwise, perform movement
        action = self._decide_movement(perception, ant_id)
        self.ants_last_action[ant_id] = action
        return action

    def _decide_movement(self, perception: AntPerception, ant_id) -> AntAction:
        """Decide which direction to move based on current state"""

        # Random movement if no specific goal
        movement_choice = random.random()

        if check_move(perception) == False:  # Only one cell visible
            return AntAction.TURN_RIGHT
        if movement_choice < 0.8:  # 60% chance to move forward
            self.current_position[ant_id] = move(perception.direction.value, self.current_position[ant_id][0], self.current_position[ant_id][1])
            return AntAction.MOVE_FORWARD
        elif movement_choice < 0.9 :  # 20% chance to turn left
            return AntAction.TURN_RIGHT
        else:  # 20% chance to turn right
            return AntAction.TURN_RIGHT


def move(direction: int, x:int, y:int) -> tuple[int, int]:
    """
    Gives the new coordinates of the ant after moving in the given direction
    """
    if direction == 0:  # North
        return x, y - 1
    elif direction == 1:  # North-East
        return x + 1, y - 1
    elif direction == 2:  # East
        return x + 1, y
    elif direction == 3:  # South-East
        return x + 1, y + 1
    elif direction == 4:  # South
        return x, y + 1
    elif direction == 5:  # South-West
        return x - 1, y + 1
    elif direction == 6:  # West
        return x - 1, y
    elif direction == 7:  # North-West
        return x - 1, y - 1
    else:
        raise ValueError("Invalid direction")
    
def get_direction(a:int,b:int,x: int, y: int) -> int:
    """
    Get the direction based on the coordinates
    """
    dx = x - a
    dy = y - b
    if dx == 0 and dy < 0:
        return 0  # North
    elif dx > 0 and dy < 0:
        return 1  # North-East
    elif dx > 0 and dy == 0:
        return 2  # East
    elif dx > 0 and dy > 0:
        return 3  # South-East
    elif dx == 0 and dy > 0:
        return 4  # South
    elif dx < 0 and dy > 0:
        return 5  # South-West
    elif dx < 0 and dy == 0:
        return 6  # West
    elif dx < 0 and dy < 0:
        return 7  # North-West
    else:
        return None

def check_move(perception: AntPerception) -> bool:
    """
    Check if the move is valid
    """
    if perception.direction.value ==0:
        if (0,-1) in perception.visible_cells and perception.visible_cells[(0,-1)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==1 :
        if (1,-1) in perception.visible_cells and perception.visible_cells[(1,-1)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==2:
        if (1,0) in perception.visible_cells and perception.visible_cells[(1,0)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==3:
        if (1,1) in perception.visible_cells and perception.visible_cells[(1,1)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==4:
        if (0,1) in perception.visible_cells and perception.visible_cells[(0,1)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==5:
        if (-1,1) in perception.visible_cells and perception.visible_cells[(-1,1)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==6:
        if (-1,0) in perception.visible_cells and perception.visible_cells[(-1,0)] != TerrainType.WALL:
            return True
    elif perception.direction.value ==7:
        if (-1,-1) in perception.visible_cells and perception.visible_cells[(-1,-1)] != TerrainType.WALL:
            return True
    return False