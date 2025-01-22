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
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
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
        for var in self.domains: #iterates over every variable
            removes = set()
            for word in self.domains[var]: #removes words too long for variable
                if len(word) != var.length:
                    removes.add(word)
            for word in removes:
                self.domains[var].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        changed = False
        removes = set()
        if self.crossword.overlaps[(x,y)] is None: #if the two variables dont overlap
            for valuex in self.domains[x]:
                breakout= False
                for valuey in self.domains[y]:
                    if valuex!=valuey:
                        breakout=True
                        break
                if breakout: #if found a valid value
                    breakout = False
                    break
                changed = True
                removes.add(valuex)
        else: #if they do overlap (make sure overlaps have same letter)
            i,j = self.crossword.overlaps[(x,y)]
            for valuex in self.domains[x]:
                breakout= False
                for valuey in self.domains[y]:
                    if valuex!=valuey and valuex[i] == valuey[j]:
                        breakout=True
                        break
                if breakout: #if found a valid value
                    breakout = False
                    break
                changed = True
                removes.add(valuex)

        for word in removes:
            self.domains[x].remove(word)
        return changed

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        #iterates over all combinations of variables and makes them consistent
        #keeps repeating this process until nothing changes in an iteration (hence the while loop)
        if arcs==None:
            while (changed:=False):
                for i in self.domains:
                    for ii in self.domains:
                        if i==ii:
                            continue
                        changed = self.revise(i,ii)
        else:
            while (changed:=False):
                for i in arcs:
                    for ii in arcs:
                        if i==ii:
                            continue
                        changed = self.revise(i,ii)
        return set() in self.domains.values()

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        #returns whether all keys have a value and each value has a key
        return set(assignment.keys())==self.crossword.variables and all(assignment.values())

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        #if each overlap has the same letter for both variables return true, else false
        for var,word in assignment.items():
            for neighbor in self.crossword.neighbors(var).intersection(assignment.keys()):
                overlap = self.crossword.overlaps[(var,neighbor)]
                if word[overlap[0]]!=assignment[neighbor][overlap[1]]:
                    return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        #if word is incompatible with a word (different letters), add one
        #word with most incompatibilities can cancel out the most other values, meaning quicker solve
        num_elim = {word:0 for word in self.domains[var]}
        neighbors = self.crossword.neighbors(var)
        for word in self.domains[var]:
            for neighbor in (neighbors-assignment.keys()):
                overlap = self.crossword.overlaps[var,neighbor]
                for wordn in self.domains[neighbor]:
                    if word[overlap[0]] != wordn[overlap[1]]:
                        num_elim[word]+=1
        sortd = sorted(num_elim.items(),key=lambda x:x[1])
        return [x[0] for x in sortd]


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        #kind of self explanatory.
        #gets variables sorted based on amount of values in domain, if there is a tie get variables sorted decreasingly by amount of neighbord
        unassigned = self.crossword.variables - assignment.keys()
        remaining_values = {var:len(self.domains[var]) for var in unassigned}
        remaining_values = sorted(remaining_values.items(), key=lambda x:x[1])

        if len(remaining_values) == 1 or remaining_values[0][1] != remaining_values[1][1]:
            return remaining_values[0][0]
        else:
            degrees = {var:len(self.crossword.neighbors(var)) for var in unassigned}
            degrees = sorted(degrees.items(),key=lambda x:x[1])
            return degrees[-1][0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        #uses recursion to find a solution that works
        #uses selection functions to be more efficient
        if self.assignment_complete(assignment):
            return assignment
        variable = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(variable,assignment):
            test = assignment.copy()
            test[variable] = value
            if self.consistent(test):
                assignment[variable] = value
                result = self.backtrack(assignment)
                if result is not None:
                    return result
            assignment.pop(variable,None)
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
