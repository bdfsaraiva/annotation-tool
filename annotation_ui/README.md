# Ferramenta de Anotação

Interface web para anotação de conversas e cálculo de métricas de Inter-Annotator Agreement (IAA).

**Versão**: 0.001 | **Status**: Desenvolvimento ativo

![Captura de ecrã da interface de anotação](https://github.com/user-attachments/assets/8d67cbf2-724f-4919-b610-dab906eecf1f)

## 📋 Índice

1. [Configuração e Deployment](#configuração-e-deployment)
2. [Execução Local](#execução-local)
3. [Execução com Docker](#execução-com-docker)
4. [Configuração para Acesso Remoto](#configuração-para-acesso-remoto)
5. [Testing com Dados Reais](#testing-com-dados-reais)
6. [Conversion Tools - Importação de Excel](#conversion-tools---importação-de-excel)
7. [Credenciais de Acesso](#credenciais-de-acesso)
8. [Funcionalidades](#funcionalidades)
9. [Troubleshooting](#troubleshooting)

---

## ⚙️ Configuração e Deployment

### Pré-requisitos
- **Node.js** (versão 18+)
- **npm** ou **yarn**
- **Docker** e **Docker Compose** (para deployment com containers)

### Configuração do Environment (.env)

**⚠️ IMPORTANTE**: Antes de executar a aplicação, **deve** criar um ficheiro `.env` para configurar a conexão com o backend.

#### 1. Criar o ficheiro .env

```bash
# Na pasta annotation_ui/
cp .env.example .env
```

#### 2. Configurar a URL da API

Edite o ficheiro `.env` conforme o seu ambiente:

**Para desenvolvimento local** (backend na mesma máquina):
```env
REACT_APP_API_URL=http://localhost:8000
```

**Para acesso remoto** (backend noutra máquina):
```env
REACT_APP_API_URL=http://192.168.1.100:8000
```
> Substitua `192.168.1.100` pelo IP real da máquina onde o backend está a correr.

#### 3. Exemplos de configuração por cenário

| Cenário | Configuração |
|---------|-------------|
| **Desenvolvimento local** | `REACT_APP_API_URL=http://localhost:8000` |
| **Server LAN** | `REACT_APP_API_URL=http://192.168.1.100:8000` |
| **Server WiFi** | `REACT_APP_API_URL=http://10.0.0.50:8000` |
| **VPN/Remote** | `REACT_APP_API_URL=http://172.16.0.10:8000` |

---

## 🚀 Execução Local

### 1. Instalar dependências
```bash
   npm install
   ```

### 2. Configurar .env
```bash
cp .env.example .env
# Editar .env conforme necessário (ver secção anterior)
```

### 3. Iniciar o servidor de desenvolvimento
```bash
npm start
```

A aplicação estará disponível em: **http://localhost:3721**

---

## 🐳 Execução com Docker

### Deployment Local (mesma máquina)

```bash
# Na raiz do projeto
docker compose up --build -d
```

### Deployment Remoto (acesso de outras máquinas)

#### 1. Configurar IP do servidor

Criar ficheiro `.env` na raiz do projeto:
```bash
cp .env.example .env
```

Editar `.env` e definir o IP da máquina:
```env
SERVER_IP=192.168.1.100  # Substitua pelo IP real
```

#### 2. Executar deployment
```bash
docker compose up --build -d
```

#### 3. Verificar o deployment
```bash
# Ver status dos containers
docker compose ps

# Ver logs
docker compose logs -f frontend
docker compose logs -f backend
```

### Acesso à aplicação

- **Local**: http://localhost:3721
- **Remoto**: http://IP_DO_SERVIDOR:3721 (ex: http://192.168.1.100:3721)

---

## 🌐 Configuração para Acesso Remoto

### Cenário: Servidor numa máquina, utilizadores noutras máquinas

#### 1. Descobrir o IP da máquina servidor
```bash
# Linux/Mac
ip addr show | grep "inet " | grep -v "127.0.0.1"

# Windows
ipconfig

# Exemplo de output: 192.168.1.100
```

#### 2. Configurar o deployment

**Opção A: Com ficheiro .env (recomendado)**
```bash
# Na raiz do projeto
echo "SERVER_IP=192.168.1.100" > .env
docker compose up --build -d
```

**Opção B: Com variáveis de ambiente inline**
```bash
SERVER_IP=192.168.1.100 docker compose up --build -d
```

#### 3. Verificar conectividade

```bash
# Testar API do backend
curl http://192.168.1.100:8000/

# Deve retornar: {"name":"Annotation Backend","version":"1.0.0",...}
```

#### 4. Acesso pelos utilizadores

Os utilizadores podem agora aceder via:
- **Frontend**: http://192.168.1.100:3721
- **API Docs**: http://192.168.1.100:8000/docs

---

## 🧪 Testing com Dados Reais

### Workflow de Testing com Dados Anotados

Para testar a aplicação com dados reais e calcular métricas de IAA:

#### 1. Preparar dados de teste

A aplicação funciona com ficheiros **Excel (.xlsx)** que contêm:
- **Dados de chat** (mensagens, utilizadores, turnos)
- **Anotações múltiplas** (diferentes anotadores, threads identificados)

#### 2. Estrutura esperada dos ficheiros Excel

Cada ficheiro Excel deve ter:
- **Múltiplos sheets**: Um sheet por anotador
- **Colunas obrigatórias**: `user_id`, `turn_id`, `turn_text`, `reply_to_turn`, `thread`
- **Dados consistentes**: Mesmas mensagens em todos os sheets
- **Anotações individuais**: Cada sheet com threads identificados pelo respectivo anotador

**Exemplo de estrutura:**
```
arquivo_chat_anotado.xlsx
├── thread_joao      # Anotações do João
├── thread_maria     # Anotações da Maria  
└── thread_pedro     # Anotações do Pedro
```

#### 3. Localização dos ficheiros de teste

Coloque ficheiros Excel em qualquer destas pastas:
```
uploads/Archive/     # Pasta preferencial
uploads/             # Pasta alternativa
conversion_tools/excel_files/
```

---

## 📊 Conversion Tools - Importação de Excel

### Setup das Conversion Tools

#### 1. Instalar dependências
```bash
cd conversion_tools
pip install -r requirements.txt
```

#### 2. Configurar ligação à API
```bash
cp config.yaml.example config.yaml
```

Editar `config.yaml`:
```yaml
api:
  base_url: "http://localhost:8000"  # Ou IP do servidor
  admin_username: "admin"
  admin_password: "admin"

import:
  default_user_password: "password"  # Password simplificada
```

#### 3. Executar importação
```bash
python import_excel.py
```

### Workflow de Importação

1. **Detecção automática** de ficheiros Excel
2. **Preview** dos dados a importar (anotadores, mensagens, anotações)
3. **Seleção/criação** de projeto
4. **Importação completa**:
   - Criação de chat rooms
   - Criação de utilizadores (usernames simplificados: `joao`)
   - Importação de mensagens
   - Importação de anotações de cada anotador
5. **Relatório detalhado** dos resultados

### Resultados da Importação

Após importação bem-sucedida:
- **Utilizadores criados** com usernames limpos (ex: `maria`)
- **Passwords simples**: `password`
- **Chat rooms** com mensagens importadas
- **Anotações** associadas a cada utilizador
- **Métricas IAA** calculáveis automaticamente

---

## 🔑 Credenciais de Acesso

### Utilizador Administrador (pré-configurado)
- **Username**: `admin`
- **Password**: `admin`

### Utilizadores Importados (via conversion tools)
- **Formato Username**: `[nome_anotador]`
- **Password**: `password`

**Exemplos após importação:**
- `joao` / `password`
- `maria` / `password`
- `pedro` / `password`

---

## ✨ Funcionalidades

### Para Administradores
- **Gestão de projetos** e chat rooms
- **Importação de dados** via CSV/Excel
- **Visualização de métricas** de anotação
- **Gestão de utilizadores**
- **Cálculo de IAA** (Inter-Annotator Agreement)

### Para Anotadores
- **Interface de anotação** intuitiva e rápida
- **Sistema de tags** para identificação de threads
- **Navegação eficiente** entre mensagens
- **Visualização de progresso**
- **Resumo das anotações** realizadas

### Funcionalidades Técnicas
- **Autenticação JWT** com refresh tokens
- **CORS configurado** para acesso remoto
- **API RESTful** com documentação automática
- **Base de dados SQLite** com migrações Alembic
- **Docker deployment** com configuração flexível

---

## 🔧 Troubleshooting

### Problemas Comuns

#### ❌ "Failed to fetch" / Erro de conexão

**Causa**: Frontend não consegue conectar ao backend

**Solução**:
1. Verificar se o backend está a correr:
   ```bash
   curl http://localhost:8000/
   ```
2. Verificar ficheiro `.env` no frontend:
   ```bash
   cat annotation_ui/.env
   # Deve conter: REACT_APP_API_URL=http://localhost:8000
   ```
3. Para acesso remoto, usar IP correto:
   ```env
   REACT_APP_API_URL=http://192.168.1.100:8000
   ```

#### ❌ CORS errors no browser

**Causa**: Backend não permite conexões do frontend

**Solução**:
1. Verificar configuração CORS no deployment:
   ```bash
   # Se usar Docker Compose com IP específico
   SERVER_IP=192.168.1.100 docker compose up --build -d
   ```

#### ❌ Conversion tools não conectam

**Causa**: Configuração incorreta da API

**Solução**:
1. Verificar `conversion_tools/config.yaml`:
   ```yaml
   api:
     base_url: "http://IP_CORRETO:8000"
   ```
2. Testar conexão:
   ```bash
   curl http://IP_CORRETO:8000/docs
   ```

#### ❌ Login não funciona

**Solução**:
1. Usar credenciais correctas:
   - Admin: `admin` / `admin`
   - Importados: `[nome]` / `password`

### Logs e Debug

```bash
# Ver logs do Docker Compose
docker compose logs -f

# Ver apenas logs do frontend
docker compose logs -f frontend

# Ver apenas logs do backend  
docker compose logs -f backend

# Verificar containers ativos
docker compose ps
```

### Reset completo

```bash
# Parar tudo
docker compose down -v

# Remover dados (CUIDADO: apaga base de dados)
rm -rf data/

# Reconstruir
docker compose up --build -d
```

---

## 📈 Estado do Desenvolvimento

### Funcionalidades Implementadas ✅
- Interface de anotação completa
- Sistema de tags e threads
- Autenticação e autorização
- Importação de dados Excel
- Cálculo de métricas IAA
- Deployment com Docker
- Configuração para acesso remoto

### Em Desenvolvimento 🚧
- Otimizações de performance
- Melhorias na UI/UX
- Funcionalidades de relatórios avançados
- Sistema de notificações

### Planeado 📅
- Exportação de resultados
- Dashboard analytics
- Integração com ferramentas externas
- Sistema de backup automático

---

**Última atualização**: Janeiro 2025  
**Desenvolvido por**: Fábio Lopes | **Orientação**: ISCTE-IUL
