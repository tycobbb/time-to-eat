import click
import io
import os
import png
import textwrap
import typing as T

from os import path as osp

# -- constants --
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

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
# a id (a counter)
class Id:
  # -- lifetime --
  def __init__(self, val: int = 0):
    self.val = val

  # -- commands --
  # advance to the next id
  def advance(self):
    self.val += 1

  # -- queries --
  # encode as a str w/ a cycle
  def encode(self) -> str:
    str = ""

    i = self.val
    while i != 0:
      i,j = divmod(i, len(ALPHABET))
      str = ALPHABET[j] + str

    return str or "0"

  # a copy of this id
  def copy(self):
    return Id(self.val)

# a handle to an image
class Image:
  # -- lifetime --
  def __init__(self, file: io.BufferedReader):
    # the file handle
    self.file = file

    # the image data
    self.data = list(png.Reader(file).read()[2])

  # -- commands --
  # closes the image and clears its data
  def close(self):
    self.file.close()
    self.data.clear()

  # -- queries --
  # encode a square slice into an int
  def slice(self, x: int, y: int, s: int) -> int:
    # get the squares min / max px coords
    x0 = x * s
    x1 = x0 + s
    y0 = y * s
    y1 = y0 + s

    # pack the data row-by-row into an int
    s = 0
    i = 0

    # for each row
    for yi in range(y0, y1):
      # for each pixel
      for xi in range(x0, x1):
        # if the pixel is on, set this bit to 1
        if self.data[yi][xi] == 2:
          s |= 1 << i

        i += 1

    return s

  # -- factories --
  # open the image at the path
  @classmethod
  def open(cls, path: str):
    return cls(
      file = open(path, "rb")
    )

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

    # the number of frames this room has
    self.n = 0

  # -- commands --
  # add to the frame count
  def add_frame(self):
    self.n += 1

  # -- queries --
  # encode as a tuple of bitsydata: (room, tiles)
  def encode(self, rid: Id, tid: Id) -> T.Tuple[str, str]:
    dir = self.cfg.path
    nme = self.name

    # open images for each frame
    imgs: list[Image] = []
    for i in range(self.n):
      p: T.Optional[str] = None

      # if frame 1, see if an image w/o frame index exists
      if i == 0:
        p0 = osp.join(dir, "{0}.png".format(nme))
        if osp.exists(p0):
          p = p0

      # otherwise, check for an image w/ frame index
      if p == None:
        p = osp.join(dir, "{0}@{1}.png".format(nme, i))

      # add the image
      imgs.append(Image.open(p))

    # build a list of tiles
    tiles: list[Tile] = []

    # for each tile in the room (x, y)
    for y in range(Room.SIZE):
      for x in range(Room.SIZE):
        slices = [ i.slice(x, y, s = Tile.SIZE) for i in imgs ]

        # if the slices are all empty
        empty = True
        for f in slices:
          if f != 0:
            empty = False

        # use empty tile
        if empty:
          tiles.append(Tile.empty())
        # otherwise create a tile
        else:
          tiles.append(Tile(
            id     = tid.copy(),
            name   = "{0} ({1},{2})".format(self.name, x, y),
            frames = slices
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

    # build the tile str
    tstr = ""
    for tile in tiles:
      # from any non-empty tiles
      if not tile.is_empty():
        tstr += "{0}\n".format(tile.encode())

    # incrememnt the room id
    rid.advance()

    # close the image files
    for img in imgs:
      img.close()

    return (rstr, tstr)

# a tile within a room
class Tile:
  # -- constants --
  SIZE = 8

  # -- lifetime --
  def __init__(self, id: Id, name: str, frames: list[int]):
    # the id
    self.id = id

    # the name
    self.name = name

    # the number of frames
    self.n = len(frames)
    assert self.n == 1 or self.n == 2, "must have 1 or 2 frames"

    # the list of frames
    self.frames = frames

  # -- queries --
  # if the tile is empty
  def is_empty(self) -> bool:
    return self.id.val == 0

  # if the list of frames is empty
  @staticmethod
  def is_frames_empty(frames: list[int]) -> bool:
    for f in frames:
      if f != 0:
        return False

    return True

  # encode the tile as bitsydata
  def encode(self):
    # format the frames
    nf = self.n
    fs = self.frames

    # encode the first frame
    fstr = self.encode_frame(fs[0])

    # if the second frame is different, add it
    if nf == 2 and fs[0] != fs[1]:
      fstr += "\n>\n{0}".format(self.encode_frame(fs[1]))

    # format the tile
    tfmt = """
      TIL {0}
      {1}
      NAME {2}
      WAL false
    """

    return hdoc(tfmt).format(
      self.id.encode(),
      fstr,
      self.name
    )

  # encode the frame as a string
  def encode_frame(self, f: int) -> str:
    i0 = 0
    i1 = Tile.SIZE * Tile.SIZE

    # for each bit
    str = ""
    for i in range(i0, i1):
      # if it's on, "1"
      if (f & (1 << i)) != 0:
        str += "1"
      # otherwise it's off, "0"
      else:
        str += "0"

      # and a newline at row end
      ii = i + 1
      if (i + 1) % Tile.SIZE == 0 and ii != i1:
        str += "\n"

    return str

  # -- factories --
  # create an empty tile
  @classmethod
  def empty(cls):
    return cls(
      id     = Id(),
      name   = "empty",
      frames = [0b0],
    )

# -- command --
# generates rooms from a dir of pngs
class GenRooms:
  def __init__(self, cfg: Config):
    # the config
    self.cfg = cfg

  def __call__(self):
    # find all rooms
    rooms: dict[str, Room] = {}

    # for each path in the dir
    d = self.cfg.path

    # get a sorted list of paths (reduce diff thrashing)
    fs = os.listdir(d)
    fs.sort()

    # for each file
    for f in fs:
      name, ext = osp.splitext(f)

      # if it's a png, add a room
      if osp.isfile(osp.join(d, f)) and ext == ".png":
        # get the name and frame, if any
        name, _ = name.split("@")

        # find or create the room
        room = rooms.get(name)
        if room == None:
          room = rooms[name] = Room(self.cfg, name)

        # incr the frame count
        room.add_frame()

    # track a shared room id and tile id (tile 0 is empty)
    rid = Id()
    tid = Id(1)

    # aggregate the room and tile bitsydata
    rstr = ""
    tstr = ""

    # add the empty tile
    tstr += "{0}\n".format(Tile.empty().encode())

    # for each room
    for i, r in enumerate(rooms.values()):
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
# strip and dedent string
def hdoc(s: str) -> str:
  return textwrap.dedent(s.strip("\n"))

# -- bootstrap --
main()
