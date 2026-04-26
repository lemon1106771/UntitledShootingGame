class Leaderboard:
    TOP_N = 5

    def __init__(self, filename="leaderboard.txt"):
        self.filename = filename
        self.scores   = self._load()

    def _load(self):
        try:
            with open(self.filename) as f:
                scores = []
                for line in f:
                    try:
                        scores.append(int(line.strip()))
                    except ValueError:
                        pass
            scores.sort(reverse=True)
            scores = scores[:self.TOP_N]
        except FileNotFoundError:
            scores = []

        # pad to TOP_N zeros
        while len(scores) < self.TOP_N:
            scores.append(0)
        return scores

    def save_scores(self):
        with open(self.filename, "w") as f:
            for s in self.scores:
                f.write(f"{s}\n")

    def add_score(self, new_score):
        self.scores.append(new_score)
        self.scores.sort(reverse=True)
        self.scores = self.scores[:self.TOP_N]
        self.save_scores()

    def get_scores(self):
        return self.scores