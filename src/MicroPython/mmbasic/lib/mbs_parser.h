#ifndef MBS_PARSER_H
#define MBS_PARSER_H

#include "mbs_util.h"
#include "mbs_nodes.h"

#ifdef __cplusplus
extern "C"
{
#endif

    mbs_node *mbs_parse_source(const char *source, int len, mbs_map *def_type,
                               mbs_error *err);
    // parse expression string (EVAL)
    mbs_node *mbs_parse_expression_str(const char *s, mbs_error *err);

#ifdef __cplusplus
}
#endif

#endif // MBS_PARSER_H
