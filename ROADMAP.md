# Roadmap - 1000 Árboles Bellavistas

## Estado Actual ✅
- ✅ Página de inicio (index.html) con scrollytelling cinematográfico
- ✅ Mapa interactivo (mapa.html) con Leaflet
- ✅ Página de visualización antes/después (visualizacion.html)
- ✅ Formulario de firmas con integración backend simulada
- ✅ Canales de compartir (email, Twitter, WhatsApp, Facebook, Instagram, Bluesky)
- ✅ Imágenes optimizadas (94% compresión)
- ✅ Scrollytelling con textos grandes, amarillos, y flecha de scroll
- ✅ CLAUDE.md documentado

---

## Próximos Pasos a Desarrollar

### 1. **Backend del Formulario de Firmas** 🔧
**Prioridad:** ALTA

- [ ] Conectar formulario a base de datos (PostgreSQL/MySQL/MongoDB)
- [ ] Guardar nombre, email y fecha de la firma
- [ ] Validación de emails (evitar duplicados)
- [ ] Envío de email de confirmación al usuario
- [ ] Panel admin para descargar listado de firmas
- [ ] Sistema de notificaciones cuando se alcancen hitos (500, 1000, etc.)

**Archivos a crear/modificar:**
- Backend API (Node.js/Python/PHP)
- Sistema de autenticación admin
- Tabla de base de datos para firmas

---

### 2. **Integración con Redes Sociales** 📱
**Prioridad:** MEDIA

- [ ] Tracking de shares (contar cuántas veces se compartió en cada red)
- [ ] Pixel de Facebook/Google Analytics
- [ ] Open Graph meta tags mejorados con vista previa dinámica
- [ ] Integración con Instagram Stories (si es posible)
- [ ] Widget de contador de firmas en tiempo real

**Archivos a crear/modificar:**
- index.html (Open Graph tags adicionales)
- Analytics tracking script
- Social counter display

---

### 3. **Estadísticas y Dashboard** 📊
**Prioridad:** MEDIA

- [ ] Dashboard público mostrando:
  - Número total de firmas
  - Progreso visual hacia los 1000
  - Tendencia semanal/mensual
  - Top ciudades/distritos (si es posible geolocalizarse)
- [ ] Dashboard privado (admin) con todas las métricas
- [ ] Gráficos de shares por red social
- [ ] Reportes descargables (PDF/CSV)

**Archivos a crear:**
- dashboard.html
- Backend para APIs de estadísticas
- Librería de gráficos (Chart.js, D3.js)

---

### 4. **SEO y Marketing** 🔍
**Prioridad:** MEDIA

- [ ] Mejorar meta tags (title, description, keywords)
- [ ] Schema.org markup (JSON-LD para peticiones ciudadanas)
- [ ] Sitemap.xml
- [ ] robots.txt optimizado
- [ ] Google Search Console integración
- [ ] Análisis de palabras clave
- [ ] Blog de noticias/actualizaciones

**Archivos a crear/modificar:**
- index.html (meta tags mejorados)
- sitemap.xml
- robots.txt
- blog/ (directorio nuevo)

---

### 5. **Funcionalidades Avanzadas del Mapa** 🗺️
**Prioridad:** MEDIA-BAJA

- [ ] Filtros interactivos en el mapa:
  - Por tipo de calle (ancha/estrecha)
  - Por especie de árbol
  - Por distrito
- [ ] Búsqueda por dirección o calle
- [ ] Heatmap de densidad arbórea
- [ ] Comparación antes/después por zona específica
- [ ] Exportar datos GeoJSON

**Archivos a modificar:**
- mapa.html
- Scripts de datos

---

### 6. **Internacionalización (i18n)** 🌍
**Prioridad:** BAJA

- [ ] Traducción a inglés
- [ ] Traducción a otros idiomas (francés, alemán, etc.)
- [ ] Selector de idiomas en header
- [ ] URLs con /en/, /fr/, etc.

**Archivos a crear:**
- i18n/ (directorio con traducciones)
- Sistema de traducción (i18next o similar)

---

### 7. **Optimizaciones Técnicas** ⚡
**Prioridad:** MEDIA

- [ ] Minificar CSS/JS
- [ ] Service Worker para offline
- [ ] Lazy loading de imágenes
- [ ] Caché agresivo del navegador
- [ ] CDN para distribución de assets
- [ ] Testing automatizado (unit tests, E2E)
- [ ] CI/CD pipeline

**Herramientas:**
- Webpack/Vite (bundler)
- Jest (testing)
- GitHub Actions (CI/CD)

---

### 8. **Mobile App** 📲
**Prioridad:** BAJA (futuro)

- [ ] Aplicación móvil nativa (React Native o Flutter)
- [ ] Notificaciones push
- [ ] Offline functionality mejorada
- [ ] Geolocalización para "firmar cerca de casa"

---

### 9. **Comunicación y Email Marketing** 📧
**Prioridad:** MEDIA

- [ ] Newsletter para suscriptores
- [ ] Secuencia de emails automática
- [ ] Reminders para compartir en redes
- [ ] Actualizaciones de progreso a firmantes
- [ ] Integración con Mailchimp/SendGrid

---

### 10. **Página de Impacto** 💚
**Prioridad:** MEDIA

- [ ] Nueva sección mostrando el impacto de 1000 árboles:
  - CO2 capturado anualmente
  - Metros cuadrados de sombra
  - Litros de agua retenida
  - Valor económico
  - Mejora de calidad del aire
  - Beneficios para la fauna local

**Archivos a crear:**
- impacto.html
- Calculadora visual del impacto

---

### 11. **Galería de Fotos** 📸
**Prioridad:** BAJA

- [ ] Galería de fotos del barrio actual
- [ ] Fotos de árboles ya plantados
- [ ] Fotos de eventos/manifestaciones
- [ ] Sistema de upload de fotos por usuarios

**Archivos a crear:**
- galeria.html
- Backend para upload de fotos

---

### 12. **Testimonios y Historias** 💬
**Prioridad:** BAJA

- [ ] Sección de testimonios de vecinos
- [ ] Historias personales sobre por qué apoyan el proyecto
- [ ] Video testimonios
- [ ] Sistema para enviar testimonios

**Archivos a crear:**
- testimonios.html
- Backend para gestionar testimonios

---

## Timeline Sugerido

| Fase | Duración | Prioridad | Tareas |
|------|----------|-----------|--------|
| **Fase 1** | 2-3 semanas | ALTA | Backend de firmas, validación, confirmación email |
| **Fase 2** | 1-2 semanas | MEDIA | Analytics, tracking shares, meta tags SEO |
| **Fase 3** | 2-3 semanas | MEDIA | Dashboard público/privado, estadísticas |
| **Fase 4** | 1-2 semanas | MEDIA | Página de impacto, calculadora visual |
| **Fase 5** | 1 semana | MEDIA | Email marketing, newsletter |
| **Fase 6+** | Futuro | BAJA | Internacionalización, app móvil, galería |

---

## Tecnologías Recomendadas

### Frontend
- HTML5, CSS3, JavaScript (vanilla)
- Leaflet (mapas)
- Fetch API o Axios (requests)

### Backend
- **Opción 1:** Node.js + Express + MongoDB
- **Opción 2:** Python + Flask + PostgreSQL
- **Opción 3:** PHP + Laravel + MySQL

### Servicios Externos
- SendGrid/Mailchimp (email)
- Google Analytics (tracking)
- AWS S3 / Cloudflare (CDN)
- Firebase (opcional, para datos en tiempo real)

### DevOps
- GitHub Actions (CI/CD)
- Docker (containerización)
- Nginx/Apache (servidor web)
- SSL Let's Encrypt (HTTPS)

---

## Notas Importantes

- **Mantener simplicidad:** El proyecto funciona bien sin JS framework. Mantener vanilla si es posible.
- **Accesibilidad:** Asegurar WCAG 2.1 AA en todas las nuevas features.
- **Performance:** Objetivo: LightHouse >90 en todas las métricas.
- **Seguridad:** Validar inputs en backend, CSRF tokens, rate limiting.
- **Documentación:** Mantener CLAUDE.md actualizado con cada cambio.

---

## Contacto y Próximos Pasos

**Responsable:** Miguel Varez  
**Email:** miguelvarez@gmail.com  
**Repositorio:** https://github.com/miguelvarez-cmyk/arboles_bellasvistas

---

*Última actualización: 31 de mayo de 2026*
