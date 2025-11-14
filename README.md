<div align="center">
  <img src="./static/img/readme_title.png" width="110"/>

"한 끼 식사의 여정을 모두 책임지는 동네 장보기 플랫폼"
</div>

  ![INTRO](./static/img/readme_info.png)

---

## 🎤 서비스 소개
장봄은 **‘귀찮음’을 ‘가치’로 바꾸는 걷기 기반 로컬 장보기 서비스**입니다.<br>대형 플랫폼 중심 유통 구조 속에서 경쟁력을 잃어가는 동네 마트와 전통시장에 새로운 활력을 불어넣습니다.

- 🥬 걷기 기반 소비 경험 : 사용자가 직접 걸어가 장을 보면, 이동 시간만큼 포인트가 적립됩니다.
- 🤖 AI와 함께하는 한 끼 여정 : 요리명 입력만으로 필요한 재료를 자동 분류하고, 남은 재료 활용법까지 추천합니다.
- 🛍️ 지역 상권 연계 : 지역 마트 재고와 연동해 재료를 매칭하고, 구매 인증을 통해 지역경제를 활성화합니다.
- 🌱 지속가능한 소비 : 걸음 수를 칼로리로 환산하고, 포장재 낭비를 줄이는 친환경 소비로 이어집니다.

장봄은 건강, 환경, 지역경제를 하나로 잇는 플랫폼으로,
“한 끼 식사의 여정을 함께하는 새로운 로컬 소비 경험”을 제시합니다.

---

## 🤖 장봄의 AI 기능 상세
### 1. AI 기반 요리·식재료 추천 및 활용
- 요리명 입력만으로 필수 재료 / 선택 재료 자동 분류
- 지역 마트에서 구할 수 있는 재료를 기반으로 장보기 리스트 자동 생성
- 메뉴를 정하지 못한 경우, 조건(시간·인원 등)에 맞춘 AI 메뉴 추천
- 과거 구매 이력을 활용해 남은 재료 기반 요리법 자동 제안
- 장바구니 재료 클릭 시 활용법·응용 요리 아이디어 즉시 제공

### 2. AI 기반 장보기 경험 향상
- 마트 도착 시 재료 신선도·보관법·구매 팁 자동 안내
- 직접 걸어온 사용자에게 상황 맞춤 격려 메시지로 동기 부여

---
## 👩‍💻 팀원 소개

|  기획·디자인  |  프론트엔드  |  프론트엔드  |      백엔드      |      백엔드      |
|:-------------:|:------------:|:------------:|:----------:|:----------:|
|    손지수     |    양서윤    |    한연주    |      양현빈      |      이유정      |
---

## 💻 기술 스택
<span> 프론트엔드: </span> 
<img src="https://img.shields.io/badge/html-E34F26?style=for-the-badge&logo=html5&logoColor=white"> 
<img src="https://img.shields.io/badge/css-1572B6?style=for-the-badge&logo=css3&logoColor=white"> 
<img src="https://img.shields.io/badge/javascript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black">

<span>백엔드: </span>
<img src="https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white"> 
<img src="https://img.shields.io/badge/django-092E20?style=for-the-badge&logo=Django&logoColor=white">


<span>AI/API: </span> 
<img src="https://img.shields.io/badge/openai%20API-412991?style=for-the-badge&logo=openai&logoColor=white">
<img src="https://img.shields.io/badge/Kakao%20Mobility%20Directions%20API-FFCD00?style=for-the-badge&logo=kakao&logoColor=white">


<span>기획·디자인: </span> 
<img src="https://img.shields.io/badge/figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white">

---

## 📁 폴더 구조
```
jangbom/
├── accounts/        # 회원가입/로그인, 유저 정보
├── food/            # 재료 선택/AI 요리 추천
├── market/          # 마트 매칭, 구매 인증
├── point/           # 포인트 적립 및 관리
├── static/          # 정적 파일(css/js/img)
├── jangbom/         # 프로젝트 설정 (settings, urls)
└── manage.py
```
---
## ✨ MVP 기능 범위
### 🪄 구현된 MVP 기능
- [x] 요리명 입력 시 AI 기반 레시피 · 식재료 추천
- [x] 필수 재료 / 선택 재료 자동 구분 및 장보기 리스트 생성
- [x] 선택 재료별 활용법 · 응용 요리 아이디어 제공 (AI 응답 기반)
- [x] 지역 마트/시장 매칭 및 장보기 여정 화면
- [x] 마트 도착 · 구매 인증 플로우
- [x] 걸어서 방문 시 포인트 적립 로직

 ### 🚧 진행 중 기능 
- [ ] 랭킹 조회
- [ ] 주소 설정 기능
- [ ] 세부 활동 내역 · 요리법 보관함

---
## 🚀 실행 방법
### 1. 저장소 클론
```bash
git clone https://github.com/SeSAC-ITCO/jangbom.git
cd jangbom-main
```
### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```
### 3. 패키지 설치
```bash
pip install -r requirements.txt
```
### 4. 환경 변수 파일 생성 (.env)
프로젝트 루트 경로에 `.env` 파일을 생성한 뒤 아래 형식으로 입력합니다. (`OPENAI_API_KEY`, `KAKAO_API_KEY` 값은 직접 발급받아 채워야 합니다.)
```bash
OPENAI_API_KEY=your_openai_api_key_here
KAKAO_API_KEY=your_kakao_api_key_here
```
### 5. 데이터베이스 초기화
```bash
python manage.py migrate
```
### 6. 서버 실행
```bash
python manage.py runserver
```
#### ⚠️ 참고사항
- DB 파일(db.sqlite3)은 GitHub에 포함되지 않지만, migrate 명령어로 자동 생성됩니다.
- API KEY가 없으면 AI 기능 및 지도 기반 기능은 동작하지 않습니다.
