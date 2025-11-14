<div align="center">
  <img src="./static/img/readme_title.png" width="110"/>

"한 끼 식사의 여정을 모두 책임지는 동네 장보기 플랫폼"
</div>

  ![INTRO](./static/img/readme_intro.png)

---

## 🎤 서비스 소개
장봄은 **‘귀찮음’을 ‘가치’로 바꾸는 걷기 기반 로컬 장보기 서비스**입니다.<br>대형 플랫폼 중심 유통 구조 속에서 경쟁력을 잃어가는 동네 마트와 전통시장에 새로운 활력을 불어넣습니다.

&emsp;🥬 걷기 기반 소비 경험 : 사용자가 직접 걸어가 장을 보면, 이동 시간만큼 포인트가 적립됩니다.
<br>&emsp;🤖 AI와 함께하는 한 끼 여정 : 요리명 입력만으로 필요한 재료를 자동 분류하고, 남은 재료 활용법까지 추천합니다.
<br>&emsp;🛍️ 지역 상권 연계 : 지역 마트 재고와 연동해 재료를 매칭하고, 구매 인증을 통해 지역경제를 활성화합니다.
<br>&emsp;🌱 지속가능한 소비 : 걸음 수를 칼로리로 환산하고, 포장재 낭비를 줄이는 친환경 소비로 이어집니다.

장봄은 건강, 환경, 지역경제를 하나로 잇는 플랫폼으로,
“한 끼 식사의 여정을 함께하는 새로운 로컬 소비 경험”을 제시합니다.

---

## 🤖 장봄의 AI 기능 상세
### 1. AI 기반 요리·식재료 추천 및 활용

✔ 요리명 기반 식재료 추천

- 사용자가 입력한 요리명을 분석해 필수 재료 / 선택 재료 자동 구분
- 직접 검색할 필요 없이 우선순위가 명확한 장보기 리스트 자동 생성
- 지역 마트에서 구할 수 있는 재료 중심으로 최적화

✔ 상황 맞춤 요리 추천

- 메뉴를 정하지 못했을 때, AI가 대화형으로 요리 추천
- 시간, 인원, 분위기 등 조건에 맞는 맞춤형 제안
- 선택한 요리는 바로 ‘재료 담기’로 연결되어 장보기 플로우와 연동

✔ 과거 구매 이력 기반 요리법 추천

- 사용자의 구매 이력 + 남은 재료 조합을 분석해 새로운 요리법 제안
- 입력 없이도 자동으로 ‘요리법 보관함’에 저장
- 식재료 낭비 감소에 기여

✔ 선택 재료 활용법 제공

- 장바구니에서 특정 재료 클릭 → 응용 요리, 활용 아이디어 제시
- 챗봇 형식으로 추가 조리법 확인 가능
- 재료 선택 → 활용법 확인으로 자연스럽게 연결되는 흐름

### 2. AI 기반 장보기 경험 향상
✔ 식재료 구매 팁 제공

- 마트 도착 시, 해당 재료의 신선도 확인법 / 보관법 / 구매 요령 실시간 안내
- 검색 없이 바로 확인 가능 → 빠른 의사결정 지원

✔ 맞춤형 격려 메시지 제공

- 사용자가 직접 마트까지 걸어왔을 때, 상황 맞춤 메시지를 출력하여 동기 부여


---

## 💻 기술 스택
<span>프론트엔드: </span> 
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

## 👩‍💻 팀원 소개
|손지수|양서윤|한연주|양현빈|이유정|
|:------:|:------:|:------:|:------:|:------:|
|기획 · 디자인|프론트엔드|프론트엔드|백엔드|백엔드|

---

## 📁 폴더 구조
```
.github/
├── workflows/
    └── deploy.yml
accounts/
├── __pycache__/
├── migrations/
├── templates/
│   └── accounts/
├── __init__.py
├── admin.py
├── apps.py
├── forms.py
├── models.py
├── tests.py
├── urls.py
├── utils.py
└── views.py
food/
├── __pycache__/
├── migrations/
├── templates/
│   └── food/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── tests.py
├── urls.py
├── utils.py
└── views.py
jangbom/
├── __pycache__/
├── __init__.py
├── asgi.py
├── settings.py
├── urls.py
└── wsgi.py
market/
├── __pycache__/
├── integrations/
├── migrations/
├── services/
├── templates/
│   └── market/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── tests.py
├── urls.py
├── utils.py
└── views.py
point/
├── __pycache__/
├── migrations/
├── templates/
│   └── point/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── tests.py
├── urls.py
├── utils.py
└── views.py
static/
├── css/
├── img/
└── js/
manage.py  
README.md  
requirements.txt  

```

---
