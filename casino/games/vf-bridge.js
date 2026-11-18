/* Velvet Felt Casino bridge — links a table game to the casino wallet.
   Loaded before each game's own script. Does nothing when a game is opened on its own. */
(function(){
  'use strict';
  var q = new URLSearchParams(location.search);
  var inCasino = window.parent !== window && q.has('vfuser');
  if (!inCasino){ window.VF = null; return; }
  var chips = Number(q.get('vfchips'));
  var last = null;
  window.VF = {
    user: q.get('vfuser'),
    name: q.get('vfname') || '',
    chips: Number.isFinite(chips) && chips >= 0 ? chips : 0,
    report: function(v){
      v = Math.round(v * 100) / 100;
      if (!Number.isFinite(v) || v === last) return;
      last = v;
      parent.postMessage({vf: 'chips', chips: v}, '*');
    }
  };
  function reply(m){ parent.postMessage(m, '*'); }
  window.addEventListener('message', function(e){
    if (e.source !== parent) return;
    var m = e.data || {}, g = window.__vf;
    if (!m.vf || !m.id) return;
    if (!g){ reply({vf: m.vf, id: m.id, ok: true, busy: false, locked: 0}); return; }
    if (m.vf === 'status'){
      reply({vf: 'status', id: m.id, busy: !!g.busy(), locked: g.locked ? g.locked() : 0, onTable: g.onTable(), chips: g.bank()});
    } else if (m.vf === 'leave'){
      var r = g.leave() || {ok: true};
      reply({vf: 'leave', id: m.id, ok: r.ok !== false, msg: r.msg || '', chips: g.bank()});
    } else if (m.vf === 'setchips'){
      var ok = !g.busy() && Number.isFinite(m.chips) && m.chips >= 0;
      if (ok) g.setBank(Math.round(m.chips * 100) / 100);
      reply({vf: 'setchips', id: m.id, ok: ok, chips: g.bank()});
    }
  });
  document.addEventListener('DOMContentLoaded', function(){
    var r = document.getElementById('resetBtn');
    if (r) r.style.display = 'none';
    document.documentElement.classList.add('in-casino');
  });
})();
