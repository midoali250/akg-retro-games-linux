"""Private CI test against one actual user-supplied ROM; runs on GitHub only."""
import hashlib,os,sys,tempfile,urllib.request
from pathlib import Path
from libretro_host import LibretroHost

lib,file_id,expected=sys.argv[1:4]
url='https://drive.google.com/uc?export=download&id='+file_id
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp);req=urllib.request.Request(url,headers={'User-Agent':'RetroCollection-CoreTest/1'})
    with urllib.request.urlopen(req,timeout=60) as response:data=response.read(10_000_001)
    if len(data)>10_000_000 or hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('wrong ROM hash')
    rom=p/('game.smc' if not data.startswith(b'NES\x1a') else 'game.nes');rom.write_bytes(data)
    with LibretroHost(lib,rom,p) as host:
        for frame in range(180):
            host.buttons={3} if 40<=frame<50 else set()  # Start button
            host.run_frame()
        assert host.frames>0 and host.last_frame and host.width>0 and host.height>0
        assert host.audio_samples>0,'no audio callback'
        state=p/'manual.state';assert not state.exists();host.save_state(state);assert state.exists()
        for _ in range(3):host.run_frame()
        host.load_state(state)
        try:host.set_verified_cheats([{'rom_sha256':'0'*64,'verified':True,'code':'test'}])
        except ValueError:pass
        else:raise AssertionError('wrong-game cheat not rejected')
        host.set_verified_cheats([])
        original=state.read_bytes();state.write_bytes(original[:5]+b'\xff'*32+original[37:])
        try:host.load_state(state)
        except ValueError:pass
        else:raise AssertionError('wrong-game state not rejected')
        print('PASS',host.system_name,'frames',host.frames,'video',host.width,host.height,'audio_samples',host.audio_samples,'explicit save/restore and hash isolation')
    # Exercise the actual pygame software presentation and manual save path in CI.
    os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
    import pygame
    from game_session import run_session
    pygame.init();screen=pygame.display.set_mode((640,480))
    assert run_session(screen,lib,rom,p/'manual-saves',max_frames=30,test_manual=True)=='test-complete'
    pygame.image.save(screen,'session-smoke.png');pygame.quit()
    print('PASS pygame game-session render, buffered audio path and manual save/load')
