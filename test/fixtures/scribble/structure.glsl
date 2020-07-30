
// Basic structural parsing test
Shader {
    Properties {
        _prop("Prop Description", int) = 1
    }

    GLSL Common {
        common_code
    }

    GLSL MockVS {
        mock_vs_code
    }

    GLSL MockTC {
        mock_tc_code
    }

    GLSL MockTE {
        mock_te_code
    }

    GLSL MockGS {
        mock_gs_code
    }

    GLSL MockFS {
        mock_fs_code
    }

    Technique Main {
        Pass {
            Vertex = (Common, MockVS)
            TessellationControl = MockTC
            TessellationEvaluation = MockTE
            Geometry = MockGS
            Fragment = (Common, MockFS)
        }
    }
}
