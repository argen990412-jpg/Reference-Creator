# Reference Creator

캐릭터나 인물 이미지 **한 장**을 넣으면 3D 모델링에 쓸 수 있는 **다각도 레퍼런스**(정면 / 3/4 / 측면 / 후면 턴어라운드)를 생성합니다.
모든 뷰가 **원본의 그림체와 분위기를 그대로 따르도록** 만드는 데 초점을 맞췄습니다.

```
input.png ──► 스타일 분석 ──► 정면 앵커 생성 ──► 나머지 뷰 병렬 생성 ──► 크기·바닥선 정렬 ──► 턴어라운드 시트
```

## 일관성을 유지하는 방법

| 단계 | 하는 일 |
|---|---|
| 1. 스타일 분석 | 비전 모델이 원본을 보고 **캐릭터/스타일 시트**를 글로 씁니다: 그림체, 선, 셰이딩, 팔레트, 비율, 얼굴, 헤어, 의상, 좌우 비대칭 요소 등. 이 시트를 모든 뷰 프롬프트에 똑같이 넣습니다. |
| 2. Style Lock 프롬프트 | 매체(2D/3D/실사), 선 굵기, 셰이딩 단계, 채도, 디테일 수준, 등신비를 원본과 똑같이 하고, 아무것도 추가·삭제·재디자인하지 말라고 명시합니다. |
| 3. 정면 앵커 | 정면을 먼저 생성한 뒤, 나머지 뷰는 **원본과 정면 이미지 두 장**을 함께 참조합니다. 같은 포즈와 비율이 모든 뷰로 이어집니다. |
| 4. 동일한 연출 조건 | 모든 뷰가 같은 포즈(A-pose 등), 직교 카메라 느낌, 같은 배경, 그림자 없음으로 생성됩니다. |
| 5. 정렬 후처리 | 캐릭터 영역을 찾아 **키를 맞추고 발을 같은 바닥선에 놓습니다**. 결과 이미지는 Blender/Maya 이미지 플레인에 바로 쓸 수 있습니다. |

좌우는 항상 **캐릭터 기준**입니다. `left`는 캐릭터의 왼쪽 옆모습이고, 코가 이미지 왼쪽을 향합니다.

## 설치

```bash
pip install -e ".[gemini]"      # Gemini (권장)
pip install -e ".[openai]"      # OpenAI GPT Image
pip install -e ".[all,dev]"     # 전부 + 웹 UI + 테스트
cp .env.example .env            # API 키 입력
```

## 사용법

```bash
# 기본: Gemini, 6방향 턴어라운드, A-pose, 전신
reference-creator my_character.png

# 직교 4면(정면/좌/후/우), T-pose, OpenAI 사용
reference-creator my_character.png -v ortho --pose t-pose -p openai

# 원하는 뷰만, 원본 포즈 유지, 추가 지시
reference-creator hero.jpg -v front,left,back --pose keep --prompt "망토 뒷면에 문양 유지"

# 얼굴 모델링용 헤드 턴어라운드
reference-creator face.png -v ortho --framing head --aspect 1:1

# API 키 없이 파이프라인만 확인
reference-creator my_character.png -p mock
```

웹 UI: `python -m reference_creator.webui` (gradio 필요)

### 주요 옵션

| 옵션 | 설명 |
|---|---|
| `-v, --views` | 프리셋 `ortho`, `turnaround`(기본), `full`(45° 8방향), `minimal`, 또는 `front,front_left,left,back_left,back,back_right,right,front_right,top` 조합 |
| `-p, --provider` | `gemini`(기본), `openai`, `mock` |
| `-m, --model` | 이미지 모델 ID 덮어쓰기 |
| `--pose` | `a-pose`(기본), `t-pose`, `relaxed`, `keep`, 또는 자유 텍스트 |
| `--framing` | `full`(기본), `bust`, `head`, 또는 자유 텍스트 |
| `--aspect` | `3:4`(기본), `2:3`, `1:1` 등 |
| `--no-analyze` / `--no-anchor` / `--no-normalize` / `--no-sheet` | 각 단계 끄기 |
| `--workers`, `--retries` | 병렬 요청 수와 재시도 횟수 |

### 출력

```
output/<이름>/
├── reference.png           # 입력 원본(정리된 버전)
├── character_sheet.txt     # 스타일/캐릭터 분석 결과
├── 01_front.png …          # 정렬된 개별 뷰 (모델링 이미지 플레인용)
├── raw/                    # 모델이 생성한 원본 그대로
├── turnaround_sheet.png    # 라벨과 머리끝/바닥 가이드라인이 있는 합본 시트
└── manifest.json           # 사용한 프롬프트, 모델, 옵션, 소요 시간, 실패 내역
```

## 프로바이더와 모델

| 프로바이더 | 기본 모델 | 환경 변수 |
|---|---|---|
| Gemini | `gemini-3.1-flash-image` (이미지), `gemini-flash-latest` (스타일 분석) | `GEMINI_API_KEY`, `REFCREATOR_GEMINI_MODEL`, `REFCREATOR_GEMINI_TEXT_MODEL` |
| OpenAI | `gpt-image-1.5` + `input_fidelity="high"` (이미지), `gpt-5.4-mini` (분석) | `OPENAI_API_KEY`, `REFCREATOR_OPENAI_MODEL`, `REFCREATOR_OPENAI_TEXT_MODEL` |

- Gemini 고품질 모델: `-m gemini-3-pro-image`. 저렴한 모델: `-m gemini-2.5-flash-image`(이 모델은 `image_size` 옵션 없이 호출됩니다).
- OpenAI `gpt-image-2`도 쓸 수 있습니다. 이 모델에는 `input_fidelity`를 보내지 않습니다(SDK 문서 기준).

## 팁

- 입력 이미지는 **전신이 다 나오고 배경이 단순할수록** 결과가 좋습니다.
- 마음에 드는 정면이 나오지 않으면 `-v front`로 정면만 여러 번 뽑아 보세요. 고른 정면을 입력으로 다시 넣어도 됩니다.
- 생성형 모델이라 뒷모습처럼 **원본에 없는 부분은 모델이 추측**합니다. 중요한 디자인은 `--prompt`로 적어 주세요.
- 측면/후면 이미지는 생성 결과일 뿐이며 원근이 완벽한 직교 투영은 아닙니다. 모델링할 때 비율 가이드로 쓰세요.

## 개발

```bash
pip install -e ".[dev]"
pytest
```

라이브러리로도 쓸 수 있습니다.

```python
from reference_creator import ReferenceCreator, Options, get_provider, resolve_views

creator = ReferenceCreator(get_provider("gemini"), Options(pose="t-pose"))
result = creator.run("hero.png", resolve_views("ortho"), "out/hero")
print(result.sheet_path)
```
