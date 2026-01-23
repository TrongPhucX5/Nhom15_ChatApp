import urllib.request
import os

icons = {
    'send.png': 'https://img.icons8.com/ios-filled/50/0084FF/paper-plane.png',
    'attach.png': 'https://img.icons8.com/ios/50/666666/attach.png',
    'emoji.png': 'https://img.icons8.com/ios/50/666666/happy--v1.png',
    'search.png': 'https://img.icons8.com/ios/50/666666/search--v1.png',
    'video.png': 'https://img.icons8.com/ios/50/666666/video-call.png',
    'user.png': 'https://img.icons8.com/ios/50/666666/user.png',
    'settings.png': 'https://img.icons8.com/ios/50/666666/settings.png',
    'chat.png': 'https://img.icons8.com/ios-filled/50/0084FF/chat.png',
    'group.png': 'https://img.icons8.com/ios/50/666666/user-group-man-man.png',
    'logout.png': 'https://img.icons8.com/ios/50/FF0000/exit.png',
    'add.png': 'https://img.icons8.com/ios/50/000000/plus-math.png',
    'leave.png': 'https://img.icons8.com/ios/50/FF0000/logout-rounded-left.png',
    'delete.png': 'https://img.icons8.com/ios/50/FF0000/trash.png'
}

base_dir = r'assets/icons'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

for name, url in icons.items():
    try:
        urllib.request.urlretrieve(url, os.path.join(base_dir, name))
        print(f'Downloaded {name}')
    except: pass

