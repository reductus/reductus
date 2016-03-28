# -*- mode: python -*-

block_cipher = None
added_files = [
         ( '../dataflow/templates/*.json', 'dataflow/templates' ),
         ( 'static', 'static'),
         ]

a = Analysis(['helper_server.py'],
             pathex=['/home/bbm/pydev/reduction/reflweb'],
             binaries=None,
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='helper_server',
          debug=False,
          strip=False,
          upx=True,
          console=True )
