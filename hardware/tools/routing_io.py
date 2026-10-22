"""Checked native-path saves for pcbnew routing scripts (KiCad Python required)."""
from pathlib import Path
import json
import pcbnew as k


def save_routed_board(board):
    """Fill and save; roll back if copper nets or project routing rules change.

    Load from the real PCB path with its companion project, never a standalone
    scratch PCB. Call after intentional edits and before running full DRC.
    """
    path = Path(board.GetFileName()).resolve()
    project = path.with_suffix('.kicad_pro')
    if not path.is_file() or not project.is_file():
        raise ValueError('Routing saves require an existing native PCB and project')
    old_board, old_project = path.read_bytes(), project.read_bytes()
    settings = json.loads(old_project)
    expected = {t.m_Uuid.AsString(): t.GetNetname() for t in board.GetTracks()}
    try:
        board.BuildConnectivity()
        k.ZONE_FILLER(board).Fill(board.Zones())
        k.SaveBoard(str(path), board)
        saved = k.LoadBoard(str(path))
        actual = {t.m_Uuid.AsString(): t.GetNetname() for t in saved.GetTracks()}
        if expected != actual:
            changed = {uid: (net, actual.get(uid)) for uid, net in expected.items()
                       if actual.get(uid) != net}
            raise RuntimeError(f'Copper identity/net changes during save: {changed}')
        after = json.loads(project.read_bytes())
        for key in ('board', 'net_settings'):
            if settings[key] != after[key]:
                raise RuntimeError(f'Project {key} settings changed during save')
    except Exception:
        path.write_bytes(old_board)
        project.write_bytes(old_project)
        raise
    return len(expected)
