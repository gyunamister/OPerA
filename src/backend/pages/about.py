from backend.components.misc import markdown_text, container

about = '''
Action-Oriented Process Mining is the future.
'''

page_layout = container('About AOPM',
                        [
                            markdown_text(about)
                        ]
                        )
