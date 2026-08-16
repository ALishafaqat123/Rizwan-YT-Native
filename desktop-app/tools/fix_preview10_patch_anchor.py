from pathlib import Path

p = Path('desktop-app/tools/apply_v120_preview10_event_driven_selector.py')
s = p.read_text(encoding='utf-8')

old = '''# Install selector at document creation so it observes YouTube cards from the moment
# they are created, instead of waiting for NavigationCompleted/SourceChanged.
old = \'\'\'            await browser.EnsureCoreWebView2Async();\\n            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;\\n\'\'\'
new = \'\'\'            await browser.EnsureCoreWebView2Async();\\n            await browser.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(ChannelSelectorScript());\\n            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;\\n\'\'\'
if old not in s:
    raise SystemExit('Preview10 document-created injection anchor not found')
s = s.replace(old, new, 1)
'''

new = '''# Install selector at document creation so it observes YouTube cards from the moment
# they are created, instead of waiting for NavigationCompleted/SourceChanged.
doc_match = re.search(r'(?m)^(?P<indent>\\s*)await browser\\.EnsureCoreWebView2Async\\([^;]*\\);\\s*$', s)
if not doc_match:
    raise SystemExit('Preview10 EnsureCoreWebView2Async anchor not found')
indent = doc_match.group('indent')
insertion = doc_match.group(0) + "\\n" + indent + "await browser.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(ChannelSelectorScript());"
s = s[:doc_match.start()] + insertion + s[doc_match.end():]
'''

if old not in s:
    raise SystemExit('Preview10 patch-script anchor block not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Corrected Preview 10 document-created injection patch anchor')
