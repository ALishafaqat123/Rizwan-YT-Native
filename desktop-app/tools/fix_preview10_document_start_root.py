from pathlib import Path

p = Path('desktop-app/BrowserMainForm.cs')
s = p.read_text(encoding='utf-8')

old = '''    observer.observe(document.documentElement, {\n      childList: true,\n      subtree: true,\n      attributes: true,\n      attributeFilter: ['href']\n    });\n\n    const routeRefresh = () => {\n'''
new = '''    const startObserver = () => {\n      const root = document.documentElement;\n      if (!root) {\n        setTimeout(startObserver, 0);\n        return;\n      }\n      observer.observe(root, {\n        childList: true,\n        subtree: true,\n        attributes: true,\n        attributeFilter: ['href']\n      });\n      rescanExisting();\n    };\n\n    const routeRefresh = () => {\n'''
if old not in s:
    raise SystemExit('Preview10 observer root anchor not found')
s = s.replace(old, new, 1)

old2 = '''    // Initial pass only. After this, new/recycled cards are handled by mutations.\n    rescanExisting();\n'''
new2 = '''    // Start as soon as the document root exists. After that, new/recycled cards\n    // are handled directly by DOM mutation events.\n    startObserver();\n'''
if old2 not in s:
    raise SystemExit('Preview10 initial rescan anchor not found')
s = s.replace(old2, new2, 1)

p.write_text(s, encoding='utf-8')
print('Guarded Preview 10 document-start observer root')
