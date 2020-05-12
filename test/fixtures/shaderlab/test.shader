Shader "Unlit/SkyboxProc" {
	Properties {
        [Header(Foo bar)]
        [Toggle(Whatever)] 
        _Whatever("whatever here", Float) = 1

		_Brightness("Brightness stuff",  Range(1, 10)) = 2.5
		_MyColor("Stuff Here", Color) = (0,1,1,1)
        
		_BaseNoise("Base Noise", 2D) = "black" {}

	}
	SubShader {
	    Tags { "RenderType" = "Opaque" }
		LOD 100

		Pass {
			CGPROGRAM
                float3 Foo() {

                }
		    ENDCG
	   }
	}
}
