class Leaderboard:
    def __init__(self, filename="leaderboard.txt"):
        self.filename = filename
        self.scores = self.load_scores()

    def load_scores(self):
        scores = []
        try:
            with open(self.filename, "r") as f:
                # Read each line, turn it into an integer, and add it to the list
                for line in f:
                    line = line.strip()
                    if line: 
                        try:
                            scores.append(int(line))
                        except ValueError:
                            # Skip any weird lines that aren't numbers
                            pass 
                            
            # If the file had fewer than 5 scores, fill the rest with zeros
            while len(scores) < 5:
                scores.append(0)
                
            # Sort them just in case someone messed with the text file
            scores.sort(reverse=True)
            return scores[:5]
            
        except FileNotFoundError:
            # If the file doesn't exist yet, just start fresh
            return [0, 0, 0, 0, 0]

    def save_scores(self):
        # Write the current scores to the file, one score per line
        with open(self.filename, "w") as f:
            for score in self.scores:
                f.write(f"{score}\n")

    def add_score(self, new_score):
        self.scores.append(new_score)
        n = len(self.scores)
        
        # Bubble sort in descending order
        for i in range(n):
            for j in range(0, n - i - 1):
                if self.scores[j] < self.scores[j + 1]:
                    self.scores[j], self.scores[j + 1] = self.scores[j + 1], self.scores[j]
                    
        # Keep only the top 5 scores
        self.scores = self.scores[:5]
        self.save_scores() 

    def get_scores(self):
        return self.scores