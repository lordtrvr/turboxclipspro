# TurboxClipsPro - Página Web (Netlify + Supabase)

## Arquitectura

- **Frontend**: HTML/CSS/JS estático, desplegado en Netlify.
- **Backend**: Supabase (Auth + Database) — sin servidor.
- **Verificación**: Supabase envía email de confirmación automáticamente (link).
- **Descarga**: Link directo al ejecutable.

## Configuración de Supabase (una sola vez)

### 1. Crear proyecto
1. Ve a [supabase.com](https://supabase.com) y crea una cuenta gratuita.
2. Crea un nuevo proyecto.
3. En **Settings → API**, copia:
   - **Project URL** (ej: `https://xxxxx.supabase.co`)
   - **anon public key**

### 2. Crear tabla de perfiles
Ve a **SQL Editor** en Supabase y ejecuta:

```sql
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  country TEXT NOT NULL,
  birth_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);
```

### 3. Configurar email de verificación
1. En Supabase → **Authentication → Email Templates**, personaliza el email.
2. En **Authentication → Providers → Email**, asegúrate de que "Confirm email" esté activado.
3. (Opcional) Configura SMTP personalizado en **Authentication → SMTP Settings**.

### 4. Configurar la app
Edita `frontend/js/config.js` con tu URL y anon key de Supabase, y la URL de descarga.

### 5. Subir a Netlify
1. Sube la carpeta `frontend/` a Netlify (drag & drop o Git).
2. Listo.

## Flujo del usuario

1. Visita la landing page → ve precios y planes.
2. Clic en "Comprar" → se abre WhatsApp para contactarte.
3. Tú liberas la licencia manualmente.
4. El usuario se registra (email + contraseña + datos personales).
5. Supabase envía email de verificación automáticamente.
6. El usuario hace clic en el link del email → cuenta verificada.
7. Inicia sesión → accede al panel con su perfil.
8. En el panel → sección "Descarga" → descarga el ejecutable.

## Estructura

```
TurboxWeb/
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── verify.html
│   ├── dashboard.html
│   ├── css/style.css
│   ├── js/
│   │   ├── config.js    # EDITAR con tus credenciales de Supabase
│   │   └── app.js
│   └── _redirects
├── downloads/
├── netlify.toml
└── README.md
```
