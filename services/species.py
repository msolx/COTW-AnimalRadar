import re

NAMES = {'blacktail deer': '黑尾鹿', 'whitetail deer': '白尾鹿', 'moose': '驼鹿',
         'roosevelt elk': '罗斯福马鹿',
         'elk': '美洲马鹿', 'black bear': '黑熊', 'coyote': '郊狼',
         'red fox': '赤狐', 'jackrabbit': '白尾长耳兔', 'wild turkey': '野火鸡',
         'mallard': '绿头鸭', 'western capercaillie': '西方松鸡',
         'siberian musk deer': '西伯利亚麝', 'eurasian lynx': '欧亚猞猁',
         'wild boar': '野猪', 'gray wolf': '灰狼', 'reindeer': '山地驯鹿',
         'eurasian brown bear': '欧亚棕熊'}

# 公开物种名录用的名称；加入翻译不代表对应内部资源名已经实机验证。
NAMES.update({
    'canada goose':'加拿大黑雁', 'ring necked pheasant':'环颈雉',
    'european rabbit':'欧洲野兔（穴兔）', 'roe deer':'狍鹿', 'fallow deer':'黇鹿',
    'red deer':'赤鹿', 'european bison':'欧洲野牛', 'eurasian wigeon':'赤颈鸭',
    'scrub hare':'灌丛野兔', 'side striped jackal':'侧纹胡狼', 'springbok':'跳羚',
    'warthog':'疣猪', 'lesser kudu':'小旋角羚', 'blue wildebeest':'蓝角马',
    'gemsbok':'南非剑羚', 'cape buffalo':'非洲水牛', 'lion':'狮',
    'cinnamon teal':'桂红鸭', 'blackbuck':'印度羚', 'axis deer':'花鹿',
    'collared peccary':'领西貒', 'puma':'美洲狮（Puma）', 'mule deer':'骡鹿',
    'water buffalo':'水牛', 'harlequin duck':'丑鸭', 'grant caribou':'格兰特驯鹿',
    'grizzly bear':'灰熊', 'plains bison':'平原野牛', 'european hare':'欧洲野兔（褐兔）',
    'ronda ibex':'隆达野山羊', 'beceite ibex':'贝塞特野山羊', 'gredos ibex':'格雷多斯野山羊',
    'southeastern spanish ibex':'东南西班牙野山羊', 'iberian mouflon':'伊比利亚盘羊',
    'iberian wolf':'伊比利亚狼', 'pronghorn':'叉角羚', 'mountain goat':'落基山羊',
    'rocky mountain bighorn sheep':'落基山大角羊', 'mountain lion':'美洲狮（Mountain Lion）',
    'rocky mountain elk':'落基山马鹿', 'chamois':'臆羚', 'feral goat':'野化山羊',
    'sika deer':'梅花鹿', 'himalayan tahr':'喜马拉雅塔尔羊', 'feral pig':'野化猪',
    'rio grande turkey':'里奥格兰德火鸡', 'antelope jackrabbit':'羚羊长耳兔',
    'mexican bobcat':'墨西哥短尾猫', 'desert bighorn sheep':'沙漠大角羊',
    'bobwhite quail':'山齿鹑', 'eastern wild turkey':'东部野火鸡',
    'green winged teal':'美洲绿翅鸭', 'eastern cottontail rabbit':'东部棉尾兔',
    'gray fox':'灰狐', 'common raccoon':'普通浣熊', 'wild hog':'野化猪（Wild Hog）',
    'american alligator':'美洲短吻鳄', 'eurasian teal':'绿翅鸭（欧亚）',
    'black grouse':'黑琴鸡', 'goldeneye':'鹊鸭', 'hazel grouse':'花尾榛鸡',
    'tufted duck':'凤头潜鸭', 'rock ptarmigan':'岩雷鸟', 'willow ptarmigan':'柳雷鸟',
    'tundra bean goose':'短嘴豆雁', 'mountain hare':'雪兔', 'greylag goose':'灰雁',
    'raccoon dog':'貉', 'bobcat':'短尾猫', 'magpie goose':'斑雁',
    'stubble quail':'澳洲鹌鹑', 'hog deer':'豚鹿', 'eastern gray kangaroo':'东部灰大袋鼠',
    'javan rusa':'爪哇鹿', 'sambar':'水鹿', 'saltwater crocodile':'湾鳄', 'banteng':'爪哇野牛',
    'woolly hare':'高原兔', 'northern red muntjac':'北赤麂', 'tibetan fox':'藏狐',
    'blue sheep':'岩羊', 'snow leopard':'雪豹', 'barasingha':'沼鹿', 'nilgai':'蓝牛羚',
    'bengal tiger':'孟加拉虎', 'wild yak':'野牦牛', 'gadwall':'赤膀鸭',
    'ferruginous duck':'白眼潜鸭', 'dusky grouse':'暗腹松鸡',
    'north american beaver':'北美河狸', 'wood bison':'森林野牛', 'manitoban elk':'曼尼托巴马鹿',
    'woodland caribou':'林地驯鹿', 'northern pintail':'针尾鸭', 'wood duck':'林鸳鸯',
    'snow goose':'雪雁', 'american mink':'美洲水貂', 'eurasian pine marten':'松貂',
    'european badger':'欧洲獾', 'eurasian woodcock':'丘鹬', 'red grouse':'苏格兰雷鸟',
    'south american tapir':'南美貘', 'ocelot':'虎猫', 'greater grison':'大鼬',
    'western mountain coati':'西部山地长鼻浣熊', 'vicuna':'小羊驼', 'capybara':'水豚',
    'spectacled bear':'眼镜熊', 'jaguar':'美洲豹', 'black caiman':'黑凯门鳄', 'taruca':'秘鲁马驼鹿',
})

# 真实资源目录与面向用户的名称分离；blacktail已在本机探针中实际读到。
# 其余别名仅作名称兼容，不代表对应物种的内存结构已在本机验证。
ALIASES = {'blacktail':'blacktail deer', 'whitetail':'whitetail deer',
           # 以下只统一公开名称的拼写和更名，不猜测未见过的缩写资源目录。
           'white tailed jackrabbit':'jackrabbit', 'merriam turkey':'wild turkey',
           'mountain reindeer':'reindeer', 'brown bear':'eurasian brown bear',
           'tahr':'himalayan tahr', 'greenwinged teal':'green winged teal',
           'green wing teal':'green winged teal', 'eurasian widgeon':'eurasian wigeon',
           'javan rusa deer':'javan rusa', 'vicuña':'vicuna'}

def canonical(name):
    normalized = ' '.join(name.strip().lower().replace('_',' ').replace('-',' ').split())
    return ALIASES.get(normalized,normalized)

def chinese(name):
    return NAMES.get(canonical(name), f'未识别物种：{name}')

def from_resource(data):
    # 严格匹配资源路径，不把随机字符串当物种。
    match = re.search(rb'/(?:animals|birds)/([a-z_]+)/', data.split(b'\0', 1)[0])
    return canonical(match[1].decode('ascii')) if match else None
