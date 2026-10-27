"""历史偏移默认禁用；只有精确哈希和完整人工验证记录均匹配才放行。"""
import json
import re
from pathlib import Path

class UnsupportedBuild(RuntimeError):
    pass

REQUIRED = ('animals', 'camera', 'manager_vector', 'species', 'position', 'ragdoll', 'hpmax', 'hp')
CHECKS = ('player_observed', 'species_observed', 'position_observed', 'axes_observed', 'health_observed')
CORE_REQUIRED = ('animals', 'camera', 'manager_vector', 'species', 'position', 'ragdoll')

def load_offsets(directory: Path, sha256: str):
    for file in sorted(directory.glob('*.json')):
        data = json.loads(file.read_text(encoding='utf-8'))
        if data.get('mode') == 'field_test':
            continue  # 现场测试记录永远不能替代正式live配置。
        if data.get('sha256', '').lower() != sha256.lower():
            continue
        evidence = data.get('validation', {})
        if (data.get('verified') is not True or not re.fullmatch('[0-9a-fA-F]{64}', sha256)
            or not all(evidence.get(k) is True for k in CHECKS)
            or not evidence.get('notes') or not evidence.get('date')):
            raise UnsupportedBuild('不支持当前游戏构建：偏移未经实机验证')
        offsets = data['offsets']
        if any(type(offsets.get(k)) is not int or not 0 <= offsets[k] < 0x10000000 for k in REQUIRED):
            raise UnsupportedBuild('偏移配置不完整或超出边界')
        return offsets
    raise UnsupportedBuild(f'不支持当前游戏构建 SHA256={sha256}；未读取动物内存')


def load_field_test_offsets(directory: Path, sha256: str):
    """现场测试也必须精确哈希匹配并具备核心字段证据，不能回退到历史猜测。"""
    for file in sorted(directory.glob('field_test_*.json')):
        data = json.loads(file.read_text(encoding='utf-8'))
        if data.get('sha256','').lower() != sha256.lower():
            continue
        evidence = data.get('validation',{})
        if (data.get('mode') != 'field_test' or data.get('core_verified') is not True
            or not re.fullmatch('[0-9a-fA-F]{64}',sha256)
            or not all(evidence.get(k) is True for k in CHECKS if k != 'health_observed')
            or not evidence.get('date') or not evidence.get('notes')):
            raise UnsupportedBuild('现场测试配置缺少核心字段验证记录')
        offsets = data.get('offsets',{})
        if any(type(offsets.get(k)) is not int or not 0 <= offsets[k] < 0x10000000 for k in CORE_REQUIRED):
            raise UnsupportedBuild('现场测试偏移配置不完整')
        # 此模式有意不支持读取生命值，避免把未验证字段混入连续扫描。
        result = {k:offsets[k] for k in CORE_REQUIRED}
        heading = data.get('heading_validation',{})
        if heading.get('verified') is True:
            # 朝向独立放行；旧配置没有此证据时仍只读原来的12字节位置。
            if (not all(heading.get(k) is True for k in ('north_observed','east_observed','stationary_turn_observed'))
                or not heading.get('date') or not heading.get('notes')
                or type(offsets.get('camera_world')) is not int
                or offsets['camera_world'] != offsets['camera']-48):
                raise UnsupportedBuild('摄像机朝向缺少独立验证记录或矩阵位置不匹配')
            result['camera_world'] = offsets['camera_world']
        health = data.get('health_validation',{})
        if health.get('verified') is True:
            if (not all(health.get(k) is True for k in ('living_observed','corpse_observed','corpse_removed_observed'))
                or not health.get('date') or not health.get('notes')
                or any(type(offsets.get(k)) is not int or not 0 <= offsets[k] < 0x10000 for k in ('hp','hpmax'))
                or offsets['hp'] != offsets['hpmax']+4):
                raise UnsupportedBuild('生命值缺少独立的活体/尸体/消失验证或字段异常')
            result.update(hp=offsets['hp'],hpmax=offsets['hpmax'])
        identity = data.get('identity_validation',{})
        if identity.get('verified') is True:
            if (not identity.get('date') or not identity.get('notes')
                    or identity.get('joint_unique_match_observed') is not True
                    or offsets.get('identity_weight') != 0x19c or offsets.get('identity_seed') != 0x1b0):
                raise UnsupportedBuild('属性三字段缺少独立验证或布局与研究证据不符')
            result.update(identity_weight=offsets['identity_weight'],identity_seed=offsets['identity_seed'])
        return result
    raise UnsupportedBuild(f'没有当前哈希的现场测试配置：{sha256}')
