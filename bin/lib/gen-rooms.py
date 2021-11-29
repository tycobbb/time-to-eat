import click
import os
import png
import textwrap
import typing as T

from os import path as osp

# -- main --
@click.command()
@click.option(
  "--only-tiles",
  is_flag = True,
  help    = "only output tiles"
)
def main(only_tiles: bool):
  cfg = Config("game/rooms", only_tiles)
  gen = GenRooms(cfg)
  gen()

# -- config --
# the tool config
class Config:
  def __init__(self, path: str, only_tiles: bool):
    # path to the rooms dir
    self.path = path

    # if only tiles should be printed
    self.only_tiles = only_tiles

# -- model --
# a tile id (a counter)
class Id:
  # -- lifetime --
  def __init__(self, val: int = 0):
    self.val = val

  # -- commands --
  # advance to the next id
  def advance(self):
    self.val += 1

  # -- queries --
  # the encoded string for this id
  def encode(self) -> str:
    return base36(self.val)

  # a copy of this id
  def copy(self):
    return Id(self.val)

# a room
class Room:
  # -- constants --
  SIZE = 16

  # -- lifetime --
  def __init__(self, cfg: Config, name: str):
    # the config
    self.cfg = cfg

    # the name of the room (and filename)
    self.name = name

  # -- queries --
  # encode as a tuple of bitsydata: (room, tiles)
  def encode(self, rid: Id, tid: Id) -> T.Tuple[str, str]:
    # open the png file
    f = open(osp.join(self.cfg.path, self.name + ".png"), "rb")
    r = png.Reader(file=f)

    # get the image data
    img = r.read()
    dat = list(img[2])

    # build a list of tiles
    tiles: list[Tile] = []

    # for each tile in the room (x, y)
    for y in range(Room.SIZE):
      for x in range(Room.SIZE):
        # get the tile's pixel coords
        x0 = x * Tile.SIZE
        x1 = x0 + Tile.SIZE
        y0 = y * Tile.SIZE
        y1 = y0 + Tile.SIZE

        # build the tile grid, a bitmask
        ti = 0
        tgrid = 0

        # for each row
        for yi in range(y0, y1):
          # for each pixel
          for xi in range(x0, x1):
            # if the pixel is on, set this bit to 1
            if dat[yi][xi] == 2:
              tgrid |= 1 << ti
            ti += 1

        # if empty, use empty tile
        if tgrid == 0:
          tiles.append(Tile.empty())
        # otherwise create a tile
        else:
          tiles.append(Tile(
            id   = tid.copy(),
            name = "{0} ({1},{2})".format(self.name, x, y),
            grid = tgrid
          ))

        # increment the id
        tid.advance()

    # build the room str
    # TODO: item locations?
    grid = ""
    for i, tile in enumerate(tiles):
      grid += tile.id.encode()

      ii = i + 1
      if ii == len(tiles):
        pass
      elif ii % Room.SIZE == 0:
        grid += "\n"
      else:
        grid += ","

    rfmt = """
      ROOM {0}
      {1}
      NAME {2}
      PAL 0
    """

    rstr = hdoc(rfmt).format(
      rid.encode(),
      grid,
      self.name
    )

    # build the tile string
    tstr = ""
    for tile in tiles:
      # from any non-empty tiles
      if not tile.is_empty():
        tstr += "{0}\n".format(tile.encode())

    # incrememnt the room id
    rid.advance()

    # close the file
    f.close()

    return (rstr, tstr)

# a tile within a room
class Tile:
  # -- constants --
  SIZE = 8

  # -- lifetime --
  def __init__(self, id: Id, name: str, grid: int):
    # the id
    self.id = id

    # the name
    self.name = name

    # the pixel grid
    self.grid = grid

  # -- queries --
  # if the tile is empty
  def is_empty(self) -> bool:
    return self.grid == 0

  # encode the tile as bitsydata
  def encode(self):
    i0 = 0
    i1 = Tile.SIZE * Tile.SIZE

    # format the grid string
    tgrid = ""
    for i in range(i0, i1):
      if (self.grid & (1 << i)) != 0:
        tgrid += "1"
      else:
        tgrid += "0"

      ii = i + 1
      if (i + 1) % 8 == 0 and ii != i1:
        tgrid += "\n"

    # format the tile
    tfmt = """
      TIL {0}
      {1}
      NAME {2}
      WAL false
    """

    return hdoc(tfmt).format(
      self.id.encode(),
      tgrid,
      self.name
    )

  # -- factories --
  # create an empty tile
  @classmethod
  def empty(cls):
    return cls(
      id   = Id(),
      name = "empty",
      grid = 0b0,
    )

# -- command --
# generates rooms from a dir of pngs
class GenRooms:
  def __init__(self, cfg: Config):
    # the config
    self.cfg = cfg

  def __call__(self):
    # find all rooms
    rooms = []

    # for each path in the dir
    d = self.cfg.path
    for f in os.listdir(d):
      p = osp.join(d, f)

      # if it's a png, add a room
      name, ext = osp.splitext(f)
      if osp.isfile(p) and ext == ".png":
        rooms.append(Room(self.cfg, name=name))

    # track a shared room id and tile id (tile 0 is empty)
    rid = Id()
    tid = Id(1)

    # aggregate the room and tile bitsydata
    rstr = ""
    tstr = ""

    # add the empty tile
    tstr += "{0}\n".format(Tile.empty().encode())

    # for each room
    for i, r in enumerate(rooms):
      r, t = r.encode(rid, tid)
      rstr += r
      tstr += t

      ii = i+1
      if ii != len(rooms):
        rstr += "\n"

    # print the result
    if self.cfg.only_tiles:
      click.echo(tstr)
    else:
      click.echo("{0}\n{1}".format(rstr, tstr))

# -- helpers --
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

# strip and dedent string
def hdoc(s: str) -> str:
  return textwrap.dedent(s.strip("\n"))

# get the base36 string
def base36(i: int) -> str:
  if i < 0:
      return "-" + base36(-i)

  str = ""
  while i != 0:
    i,j = divmod(i, len(ALPHABET))
    str = ALPHABET[j] + str

  return str or "0"

# -- bootstrap --
main()
