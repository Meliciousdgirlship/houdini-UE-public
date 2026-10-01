"""Shared Chat Completions client. Credentials stay in the user's environment."""
import json,os,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent

def setting(name):
    value=os.environ.get(name,'').strip()
    if value: return value
    if os.name=='nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as reg:
                return str(winreg.QueryValueEx(reg,name)[0]).strip()
        except OSError: pass
    return ''

def configuration(require_key=True):
    path=ROOT/'api.local.json'
    data=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    base=(setting('BUILDING_API_BASE_URL') or data.get('base_url','')).rstrip('/')
    model=setting('BUILDING_API_MODEL') or data.get('model','')
    key=setting('BUILDING_API_KEY') or setting('CLAUDEX_API_KEY')
    if not base or not model:
        raise RuntimeError('请先运行 setup_api.ps1，填写 API Base URL、模型名称和密钥')
    url=base if base.endswith('/chat/completions') else base+'/chat/completions'
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('API 地址必须是无账号、查询参数的 HTTPS 地址')
    if require_key and not key: raise RuntimeError('未配置 BUILDING_API_KEY，请运行 setup_api.ps1')
    return dict(url=url,model=model,key=key)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise RuntimeError('API 返回重定向；请在配置中填写最终 API 地址')

def request_spec(description,base_spec,system_prompt,config=None):
    config=config or configuration()
    payload=dict(model=config['model'],messages=[{'role':'system','content':system_prompt},
        {'role':'user','content':json.dumps(dict(mode='new' if description.startswith(('新建','重新生成')) else 'edit',base_spec=base_spec,instruction=description),ensure_ascii=False)}],stream=False,max_tokens=2048)
    request=urllib.request.Request(config['url'],data=json.dumps(payload).encode('utf-8'),headers={'Authorization':'Bearer '+config['key'],'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=90) as response:
            result=json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        messages={401:'密钥无效或平台不匹配',403:'账号无权使用此接口或模型',404:'Base URL 或模型名称不正确',429:'额度不足或请求过于频繁'}
        raise RuntimeError('API HTTP '+str(error.code)+'：'+messages.get(error.code,'平台返回错误，请查看平台控制台')) from None
    except (urllib.error.URLError,TimeoutError):
        raise RuntimeError('API 连接失败或超时，请检查网络和 Base URL') from None
    if isinstance(result,dict) and isinstance(result.get('data'),dict): result=result['data']
    choices=result.get('choices') if isinstance(result,dict) else None
    if not choices: raise ValueError('接口没有返回 choices；需要兼容 Chat Completions 的接口')
    choice=choices[0]
    if choice.get('finish_reason')!='stop': raise ValueError('模型未正常完成，建筑保持不变')
    content=choice.get('message',{}).get('content')
    if not isinstance(content,str): raise ValueError('模型没有返回文本')
    content=content.strip();lines=content.splitlines()
    if len(lines)>=3 and lines[0].strip() in ('```','```json') and lines[-1].strip()=='```': content='\n'.join(lines[1:-1])
    try: spec=json.loads(content)
    except json.JSONDecodeError: raise ValueError('模型未返回合法建筑 JSON，未应用') from None
    if not isinstance(spec,dict): raise ValueError('模型返回的建筑参数不是对象')
    if 'error' in spec: raise ValueError(str(spec['error']))
    return spec

def status():
    config=configuration(require_key=False)
    return dict(endpoint=config['url'],model=config['model'],key_configured=bool(config['key']))
