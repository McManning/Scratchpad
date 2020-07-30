
Shader {
    Properties {
        // Typehinted test
        _f("test float", float) = 0.5
        _i("test int", int) = 5
        _v2("test v2", vec2) = (0.1, 0.2)
        _v3("test v3", vec3) = (0.1, 0.2, 0.3)
        _v4("test v4", vec4) = (0.1, 0.2, 0.3, 0.4)
        _color("test color", color) = (0.1, 0.2, 0.3, 0.4)
        _tex("test texture", texture2D) = "white"
        
        // Automatic type detection tests
        _auto_f("test float") = 0.5
        _auto_i("test int") = 5
        _auto_v2("test v2") = (0.1, 0.2)
        _auto_v3("test v3") = (0.1, 0.2, 0.3)
        _auto_v4("test v4") = (0.1, 0.2, 0.3, 0.4)
        _auto_color("test color") = (0.1, 0.2, 0.3, 0.4)
    }

    GLSL VS {               
        
    }

    GLSL FS {
        
    }

    Technique Main {
        Pass {
            Vertex = VS
            Fragment = FS
        }
    }
}
