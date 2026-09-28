#version 300 es
precision highp float;

in vec2 v_texcoord;
layout(location = 0) out vec4 fragColor;
uniform sampler2D tex;

// A fixed Bayer pattern gives the 16 gray levels gentle, stable dithering.
float bayer4(vec2 position) {
    ivec2 cell = ivec2(mod(floor(position), 4.0));
    int pattern[16] = int[16](
         0,  8,  2, 10,
        12,  4, 14,  6,
         3, 11,  1,  9,
        15,  7, 13,  5
    );
    return float(pattern[cell.y * 4 + cell.x]) / 16.0;
}

void main() {
    vec4 pixel = texture(tex, v_texcoord);
    float gray = dot(pixel.rgb, vec3(0.2126, 0.7152, 0.0722));
    gray = smoothstep(0.14, 0.86, gray);
    float level = clamp(floor(gray * 15.0 + bayer4(gl_FragCoord.xy)), 0.0, 15.0);
    vec3 ink = vec3(0.07, 0.075, 0.065);
    vec3 paper = vec3(0.94, 0.93, 0.89);
    fragColor = vec4(mix(ink, paper, level / 15.0), pixel.a);
}
