#if defined(VERTEX)

#if __VERSION__ >= 130
#define COMPAT_VARYING out
#define COMPAT_ATTRIBUTE in
#define COMPAT_TEXTURE texture
#else
#define COMPAT_VARYING varying 
#define COMPAT_ATTRIBUTE attribute 
#define COMPAT_TEXTURE texture2D
#endif

#ifdef GL_ES
#define COMPAT_PRECISION mediump
#else
#define COMPAT_PRECISION
#endif

uniform   mat4 MVPMatrix;
COMPAT_ATTRIBUTE vec2 VertexCoord;
COMPAT_ATTRIBUTE vec2 TexCoord;
COMPAT_ATTRIBUTE vec4 COLOR;
COMPAT_VARYING   vec2 v_tex;
COMPAT_VARYING   vec4 v_col;
void main(void)                                    
{                                                  
	gl_Position = MVPMatrix * vec4(VertexCoord.xy, 0.0, 1.0);
	v_tex       = TexCoord;                           
	v_col       = COLOR;                           
}

#elif defined(FRAGMENT)

#if __VERSION__ >= 130
#define COMPAT_VARYING in
#define COMPAT_TEXTURE texture
out vec4 FragColor;
#else
#define COMPAT_VARYING varying
#define FragColor gl_FragColor
#define COMPAT_TEXTURE texture2D
#endif

#ifdef GL_ES
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
#define COMPAT_PRECISION mediump
#else
#define COMPAT_PRECISION
#endif
			
/* escape/UI chromatic aberration: red one way, blue the other, alpha from all three.
   amount = sideways shift in texture coordinates (0.003 ≈ 3 px on a full-screen layer) */
COMPAT_VARYING   vec4      v_col;
COMPAT_VARYING   vec2      v_tex;
uniform   sampler2D u_tex;
uniform   COMPAT_PRECISION float amount;

void main(void)
{
	float o = amount > 0.0 ? amount : 0.003;
	vec4 r = COMPAT_TEXTURE(u_tex, v_tex + vec2(o, 0.0));
	vec4 g = COMPAT_TEXTURE(u_tex, v_tex);
	vec4 b = COMPAT_TEXTURE(u_tex, v_tex - vec2(o, 0.0));
	FragColor = vec4(r.r, g.g, b.b, max(max(r.a, g.a), b.a)) * v_col;
}
#endif
