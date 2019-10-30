import shinra.content as c


def test_content():
    html_content = """
        <html>
          <head>
            <title>test_title</title>
          </head>
          <body>
            \u2028test_body
          </body>
        </html>"""
    content = c.Content(html_content)
    assert content.get_char_offset(0, 0) == 0
    assert content.get_char_offset(3, 12) == 45
    assert content.get_char_offset(3, 36) == 69
    assert content.get_char_offset(5, 10) == 99
    assert content.get_char_offset(7, 16) == 145
    assert content.get_line_offset(0) == (0, 0)
    assert content.get_line_offset(45) == (3, 12)
    assert content.get_line_offset(69) == (3, 36)
    assert content.get_line_offset(99) == (5, 10)
    assert content.get_line_offset(144) == (7, 15)
    assert content.get_text(3, 12, 3, 37) == '<title>test_title</title>'
    assert content.get_text(5, 10, 7, 17) \
        == """<body>
            \u2028test_body
          </body>"""
    assert content.get_last_line_offset() == (8, 15)
    assert content.get_char_offset(*content.get_last_line_offset()) \
        == len(html_content)


def test_clean_html():
    html_content = """
        <!DOCTYPE html>
        <html>
          <head>
            <title>test_title</title>
          </head>
          <body>
            test_body
            <h1>test_h1</h1>
            \u2028test_h1_content1
            <br>
            test_h1_content2
            <h2>test_h2_1</h2>
            <img src="test.jpg" />
            &lt;test_entity&gt;test_entity2
            <!-- comment -->
            <h2>test_h2_2</h2>
            <!--
              comment2
            -->
            <div>&#38;</div>
            <dl>
              <dt>dt0</dt>
              <dd>dd00</dd>
              <dt>dt1</dt>
              <dd>dd10</dd>
              <dd>dd11<!-- comment3 --></dd>
            </dl>
          </body>
        </html>"""
    got = c.clean_html(c.Content(html_content))
    assert len(html_content) == len(got)
    assert got == """
                       
              
                
                   test_title        
                 
                
            test_body
                test_h1     
            \u2028test_h1_content1
                
            test_h1_content2
                test_h2_1     
                                  
            &lt;test_entity&gt;test_entity2
                            
                test_h2_2     
                
                      
               
                 &#38;      
                
                  dt0     
                  dd00     
                  dt1     
                  dd10     
                  dd11                      
                 
                 
               """  # noqa
