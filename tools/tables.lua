-- Size table columns by their content instead of by the width of the dashes
-- in the Markdown separator row. Long-text columns get the room they need;
-- columns holding an unbreakable token (a long word or an inline code span)
-- get at least enough room that the token cannot overflow the cell.

-- Geometry of the printed text block and the two fonts, in points. A column
-- is (linewidth - 4*colsep) * fraction - 2*colsep wide.
local LINE_PT = 441
local PAD_PT = 4 * 6
local SLACK_PT = 6
local TEXT_PT_PER_CHAR = 5.2
local CODE_PT_PER_CHAR = 6.05
local MAX_FRACTION = 0.55

-- Widest unbreakable run in a cell: a word in the body font, or a whole
-- inline code span.
local function widest_word(text, width)
  local widest = 0
  for word in text:gmatch("%S+") do
    widest = math.max(widest, #word * width)
  end
  return widest
end

local function cell_blocks(cell)
  return cell.contents or cell.content
end

-- A code span is only breakable at its spaces, so its words are measured in
-- the monospace width; everything else uses the body-text estimate.
local function longest_run(cell)
  local blocks = cell_blocks(cell)
  local widest = 0
  pandoc.Div(blocks):walk{
    Code = function(code)
      widest = math.max(widest,
        widest_word(code.text, CODE_PT_PER_CHAR) + 2 * CODE_PT_PER_CHAR)
      return code
    end,
  }
  widest = math.max(widest,
    widest_word(pandoc.utils.stringify(blocks), TEXT_PT_PER_CHAR))
  return widest
end

local function cell_length(cell)
  return math.min(#pandoc.utils.stringify(cell_blocks(cell)), 40)
end

function Table(tbl)
  local n = #tbl.colspecs
  if n == 0 then return tbl end

  local weight, longest = {}, {}
  for i = 1, n do
    weight[i] = 0
    longest[i] = 0
  end

  local function observe(row, factor)
    local col = 0
    for _, cell in ipairs(row.cells) do
      col = col + 1
      if col <= n then
        weight[col] = weight[col] + factor * cell_length(cell)
        longest[col] = math.max(longest[col], longest_run(cell))
      end
    end
  end

  local body_rows = 0
  if #tbl.head.rows > 0 then observe(tbl.head.rows[1], 1.6) end
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      body_rows = body_rows + 1
      observe(row, 1)
    end
  end

  local total = 0
  for i = 1, n do
    weight[i] = math.max(weight[i] / math.max(body_rows + 1, 1), 6)
    total = total + weight[i]
  end
  if total == 0 then return tbl end

  local width, minimum = {}, {}
  local sum_min = 0
  for i = 1, n do
    width[i] = weight[i] / total
    minimum[i] = math.min(MAX_FRACTION,
      (longest[i] + PAD_PT + SLACK_PT) / LINE_PT)
    sum_min = sum_min + minimum[i]
  end
  if sum_min > 1 then
    for i = 1, n do minimum[i] = minimum[i] / sum_min end
  end

  -- Give narrow columns their minimum, share the rest by weight, repeat
  -- until no column is squeezed below its minimum.
  for _ = 1, 5 do
    local pinned, changed = {}, false
    local available, free_weight = 1, 0
    for i = 1, n do
      if width[i] < minimum[i] - 1e-9 then
        pinned[i] = true
        available = available - minimum[i]
        changed = true
      else
        free_weight = free_weight + weight[i]
      end
    end
    if not changed then break end
    for i = 1, n do
      if pinned[i] then
        width[i] = minimum[i]
      elseif free_weight > 0 then
        width[i] = available * weight[i] / free_weight
      end
    end
  end

  local sum = 0
  for i = 1, n do sum = sum + width[i] end
  for i = 1, n do
    tbl.colspecs[i] = { tbl.colspecs[i][1], width[i] / sum }
  end
  return tbl
end
