"""Exercise checked-save rollback on disposable copies of the daughter PCB."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import shutil
import pcbnew as k
import routing_io

source = Path(__file__).resolve().parents[1] / 'ir-daughter' / 'babel-ir-daughter'
with TemporaryDirectory(prefix='babel-routing-save-') as tmp:
    pcb = Path(tmp) / 'board.kicad_pcb'
    project = pcb.with_suffix('.kicad_pro')
    for suffix, dest in [('.kicad_pcb', pcb), ('.kicad_pro', project)]:
        shutil.copyfile(source.with_suffix(suffix), dest)
    routing_io.save_routed_board(k.LoadBoard(str(pcb)))
    print('PASS native-path fill/save preserves copper nets and project rules')
    real_save = k.SaveBoard

    def change_net(path, board):
        track = next(iter(board.GetTracks()))
        other = next(n for n in board.GetNetInfo().NetsByNetcode().values()
                     if n.GetNetCode() > 0 and n.GetNetname() != track.GetNetname())
        # Isolate the item so KiCad cannot infer and restore its original net
        # from an attached pad while loading the intentionally corrupted file.
        track.SetStart(k.VECTOR2I(k.FromMM(100), k.FromMM(100)))
        track.SetEnd(k.VECTOR2I(k.FromMM(101), k.FromMM(100)))
        track.SetNet(other)
        return real_save(path, board)

    def change_rules(path, board):
        result = real_save(path, board)
        data = json.loads(project.read_text())
        data['board']['design_settings']['rules']['min_clearance'] = .99
        project.write_text(json.dumps(data))
        return result

    for fault, message in [(change_net, 'Copper identity/net'),
                           (change_rules, 'Project board settings')]:
        before = pcb.read_bytes(), project.read_bytes()
        board = k.LoadBoard(str(pcb))
        with patch.object(routing_io.k, 'SaveBoard', side_effect=fault):
            try:
                routing_io.save_routed_board(board)
            except RuntimeError as error:
                assert message in str(error), error
            else:
                raise AssertionError(f'{fault.__name__} was not rejected')
        assert before == (pcb.read_bytes(), project.read_bytes())
        print(f'PASS {fault.__name__} rejected; PCB and project restored byte-for-byte')
