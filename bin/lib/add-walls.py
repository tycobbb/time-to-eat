# -- main --
def main():
    cfg = Config("game/game.bitsydata")
    add = AddWalls(cfg)
    add()

# -- config --
# the tool config
class Config:
    def __init__(self, path: str):
        # path to the game bitsydata
        self.path = path

# -- command --
# command that add walls to the bitsy game data
class AddWalls:
    def __init__(self, cfg: Config):
        # the config
        self.cfg = cfg

        # the current line index
        self.i = 0

        # the lines in the file
        self.lines: list[str] = []

    # -- main --
    def __call__(self):
        # load file
        with open(self.cfg.path, "r") as f:
            self.lines = f.readlines()

        # for each line
        while self.i < len(self.lines):
            line = self.lines[self.i]

            # process the line
            if line.startswith("TIL"):
                self.i = self.set_tile_wall()
            # or move on to the next
            else:
                self.i += 1

        # save file
        with open(self.cfg.path, "w") as f:
            text = "".join(self.lines)
            f.write(text)

    # -- commands --
    def set_tile_wall(self):
        # skip the "TIL" line
        j = self.i + 1

        # count the number of "on" bits
        count = 0

        # for each line of row data
        for _ in range(8):
            line = self.lines[j]

            # add every "on" bit
            for c in line:
                if c == '1':
                    count += 1

            j += 1

        # build wall string
        wall = "WAL {0}\n".format("true" if count > 20 else "false")

        # find the position of the "WAL" line
        while True:
            line = self.lines[j]

            # if its a "WAL", replace it
            if line.startswith("WAL"):
                self.lines[j] = wall
                break
            # or blank line, insert it
            elif line == "\n":
                self.lines.insert(j, wall)
                break

            # keep going
            j += 1

        # move on to the next line
        j += 1

        return j

# -- bootstrap --
main()
