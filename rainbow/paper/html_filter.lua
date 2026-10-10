-- Number figures/tables, resolve \ref links, use SVG figures, drop the LaTeX title block.
local nums = {}
local function prefix(kind, n) return pandoc.Strong{pandoc.Str(kind .. '\u{a0}' .. n .. '.')} end

local function caption_prefix(cap, kind, n)
  local b = cap.long[1]
  if b and (b.t == 'Plain' or b.t == 'Para') then
    b.content:insert(1, pandoc.Space()); b.content:insert(1, prefix(kind, n))
  end
end

-- Put an audio player under each clip number in the clips table.
local AUDIO = '../audio/'
function add_players(t)
  local files = {}
  for _, f in ipairs(pandoc.system.list_directory(AUDIO)) do
    local n = f:match('^(%d%d)_.*%.wav$'); if n then files[n] = f end
  end
  for _, body in ipairs(t.bodies) do
    for _, row in ipairs(body.body) do
      local cell = row.cells[1]
      local n = pandoc.utils.stringify(cell.contents)
      if files[n] then
        cell.contents:insert(pandoc.RawBlock('html',
          '<audio controls preload="none" src="' .. AUDIO .. files[n] .. '"></audio>'))
      end
    end
  end
end

function Pandoc(doc)
  local fig, tab = 0, 0
  local blocks = pandoc.List()
  for i, b in ipairs(doc.blocks) do
    if not (i == 1 and b.t == 'Div' and b.classes:includes('center')) then blocks:insert(b) end
  end
  doc.blocks = blocks
  doc = doc:walk{
    Figure = function(f) fig = fig + 1; nums[f.identifier] = fig; caption_prefix(f.caption, 'Figure', fig); return f end,
    Div = function(d)
      if d.identifier:match('^tab:') and d.content[1] and d.content[1].t == 'Table' then
        tab = tab + 1; nums[d.identifier] = tab; caption_prefix(d.content[1].caption, 'Table', tab)
        if d.identifier == 'tab:clips' then add_players(d.content[1]) end
      end
      return d
    end,
    -- \paragraph headings stay unnumbered, as in the PDF
    Header = function(h) if h.level >= 4 then h.classes:insert('unnumbered') end; return h end,
    Image = function(img) img.src = img.src:gsub('%.pdf$', '.svg'); img.attributes.width = nil; return img end,
  }
  return doc:walk{
    Link = function(l)
      local r = l.attributes['reference']
      if r and nums[r] then l.content = {pandoc.Str(tostring(nums[r]))} end
      return l
    end,
  }
end
