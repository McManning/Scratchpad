
class RenderPass:
    """
    Base render pass. Implement this class for your passes.
    """
    def setup(self):
        """
        Allocate resources needed to render your pass.
        This is executed once - during render engine setup.
        """
        pass

    def configure(self):
        """
        Read updated renderer configurations.
        Only gets called when the configs are modified in some way
        so that you can regenerate textures, re-calculate complex
        uniform values, etc.

        Properties:
            ????
        """
        # What would be here? Don't really have renderer configs
        # anymore - it's all per-material. Could PASSES expose 
        # configurations for the renderer/user? E.g. shadow can 
        # expose cascade configurations to be tweaked? Not a 
        # bad idea - would be stored on scene. Otherwise we're
        # hardcoding shadows to a 1024x1024 and 3 cascades or w/e.
        pass 

    def execute(self, data):
        """
        Perform all the rendering associated with this pass.
        Bind uniforms, set render targets, render objects, etc.

        Properties:
            data (RenderData)
        """
        pass 
    
    def cleanup(self):
        """
        Cleanup resources allocated during setup()
        """
        pass
