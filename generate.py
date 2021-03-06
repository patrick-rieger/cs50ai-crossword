import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in list(self.domains):
            for value in list(self.domains[var]):
                if len(value) != var.length:
                    self.domains[var].remove(value)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        for valueX in list(self.domains[x]):
            overlap = self.crossword.overlaps[x, y]
            if overlap:
                i, j = overlap
                if not any(valueX[i] == valueY[j] for valueY in self.domains[y]):
                    self.domains[x].remove(valueX)
                    revised = True
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs:
            queue = list(arcs)
        else:
            queue = []
            for key in self.domains:
                for key2 in self.domains:
                    if key != key2:
                        if (key2, key) not in queue:
                            queue.append((key, key2))
        while queue:
            X, Y = queue.pop()
            if self.revise(X, Y):
                if len(self.domains[X]) == 0:
                    return False
                for Z in self.crossword.neighbors(X) - {Y}:
                    queue.append((Z, X))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        if len(assignment.keys()) != len(self.crossword.variables):
            return False
        for key in assignment:
            if not assignment[key]:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # An assignment is consistent if it satisfies all of the constraints of the problem:
        #   all values are distinct,
        values = list(assignment.values())
        for value in values:
            if values.count(value) > 1:
                return False
        #   every value is the correct length,
        for variable in assignment:
            if variable.length != len(assignment[variable]):
                return False
        #   and there are no conflicts between neighboring variables.
        for variable in assignment:
            for neighbor in self.crossword.neighbors(variable):
                if neighbor not in assignment:
                    continue
                (i, j) = self.crossword.overlaps[(variable, neighbor)]
                if assignment[variable][i] != assignment[neighbor][j]:
                    return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        ordered = []
        if not var:
            return ordered
        values_in_assignment = assignment.values()
        for value in self.domains[var]:
            count = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    continue
                for neighbor_value in self.domains[neighbor]:
                    i, j = self.crossword.overlaps[var, neighbor]
                    if value[i] != neighbor_value[j]:
                        count+= 1
            ordered.append((value, count))
        
        # Order by the second argument (the number of values they rule out for neighboring variables)
        ordered.sort(key=lambda x: x[1])

        return [value for value, i in ordered]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        variables = []
        
        for var in self.crossword.variables:
            if var not in assignment:
                variables.append((var, len(self.domains[var])))
        
        # Ordered by the number of remaining values in its domain
        variables.sort(key=lambda x: x[1])

        # Pick up the minimum number
        minimum_number = variables[0][1]
        # And make a list (minimum_vars) of variables with this minimum number
        minimum_vars = [a[0] for a in variables if a[1] == minimum_number]

        # If more variables has this minimum number, its a TIE
        if len(minimum_vars) > 1:
            degrees = dict()
            for var in minimum_vars:
                degrees[var] = len(self.crossword.neighbors(var))
            
            # Order the minimum_vars list by the largest degree
            minimum_vars.sort(key=lambda x: degrees[x], reverse=True)
        
        return minimum_vars[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value
            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result is not None:
                    return result
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
