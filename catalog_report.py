"""从同一份已核对名录生成中文查阅表；不连接游戏，不接受命令行参数。"""
import config
from services.reserves import CATALOG
from services.species import chinese

# 历史资源键继续兼容旧采样；查阅表展示准确的公开名称。
PUBLIC_NAMES = {'wild turkey':'Merriam Turkey', 'jackrabbit':'White-tailed Jackrabbit',
                'reindeer':'Mountain Reindeer'}

def render_catalog():
    entries = CATALOG['reserves']
    names = {name for entry in entries for name in entry['species']}
    lines = ['# 保护区动物名录', '',
             f"核对日期：{CATALOG['reviewed_on']}。共{len(entries)}个保护区、"
             f"{len(names)}个区分后的物种/亚种名称、{sum(len(e['species']) for e in entries)}条普通保护区—物种关联。", '',
             '数据来自公开名录及官方更新，表示可能出现的物种，不表示当前加载或存活。中文为本工具显示译名；'
             '英文名用于核对，不保证与所有游戏汉化版本一致。保护区仍需手动选择。', '',
             '内部资源别名和公开名不同：wild turkey按既有Merriam资源键保留，jackrabbit为白尾长耳兔，'
             'reindeer为Mountain Reindeer。未验证的内部缩写不猜测、不因选区自动改物种；'
             '物种名称整理完成不代表19区内存接入已逐区验收。', '',
             '## 数量总表', '', '| 保护区 | English / 别名 | 普通物种数 |', '|---|---|---:|']
    for entry in entries:
        lines.append(f"| {entry['name_zh']} | {entry['name_en']} | {len(entry['species'])} |")
    for entry in entries:
        lines += ['',f"## {entry['name_zh']}（{entry['name_en']}）", '', '| 中文显示名 | 公开英文名 |', '|---|---|']
        for name in entry['species']:
            label = '梅里亚姆火鸡（菜单显示野火鸡）' if name == 'wild turkey' else chinese(name)
            lines.append(f"| {label} | {PUBLIC_NAMES.get(name,name.title())} |")
        if entry.get('mission_only'):
            lines += ['', '任务专属例外：'+ '、'.join(chinese(name) for name in entry['mission_only'])+
                      '。不计入普通名录，只在采样出现时显示“任务专属候选”。']
        lines += ['', '来源：'+ '；'.join(f"[{key}]({CATALOG['sources'][key]})" for key in entry['sources'])+'。']
    lines += ['', '## 更新与核对限制', '',
              '已纳入Granite补充物种、Te Awaroa塔尔羊、Rancho沙漠大角羊替换、Alberta、Scotland及Peru。'
              '最新核对的9.3更新未宣布新增保护区或普通物种关联。', '',
              '部分Wiki直接访问被限制，使用搜索索引可读的物种表；官方完整列表优先。'
              'Wiki总述仍存在“18区”的过期文字，但其表格列出19区；总数以官方第19目的地说明及用户游戏界面交叉核对。', '',
              '名录外采样会报警，不静默添入所选保护区。若后续更新新增物种，需核对原始资源名、官方更新及名录，'
              '修改JSON、中文映射、配置数量（新增区时）和相关回归基准，再运行测试并重新生成此表。', '']
    return '\n'.join(lines)

if __name__ == '__main__':
    config.CATALOG_REPORT_FILE.write_text(render_catalog(),encoding='utf-8')
    print(f'已生成 {config.CATALOG_REPORT_FILE.name}')
