
// Testing multiple techniques and passes
Shader {
    GLSL Common {
        common_code
    }

    GLSL MockVS {
        mock_vs_code
    }

    GLSL MockVS2 {
        mock_vs2_code
    }

    GLSL MockFS {
        mock_fs_code
    }

    GLSL MockFS2 {
        mock_fs2_code
    }

    Technique Main {
        Pass {
            Vertex = (Common, MockVS)
            Geometry = GeometryShader
            Fragment = (Common, MockFS)
        }
        
        Pass {
            Vertex = MockVS2
            Fragment = MockFS2
        }
    }

    Technique Shadow {
        Pass {
            Vertex = MockVS2
            Fragment = MockFS2
        }
    }
}
