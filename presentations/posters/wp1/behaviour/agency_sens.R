suppressPackageStartupMessages({library(lmerTest)})
D <- commandArgs(TRUE)[1]
files <- grep("kinematics", list.files(D, "\\.csv$", full.names=TRUE), invert=TRUE, value=TRUE)
d <- do.call(rbind, lapply(files, function(f){ x <- read.csv(f, stringsAsFactors=FALSE); x$subj <- basename(f)
  x[, c("subj","phase","is_timeout","actual_difficulty_level","cue_difficulty_prediction","angle_bias","agency_rating")]}))
d <- subset(d, grepl("^test", phase) & actual_difficulty_level=="medium" & tolower(is_timeout)!="true")
d$c <- ifelse(d$cue_difficulty_prediction=="high", .5, -.5); d$a <- ifelse(d$angle_bias==90, .5, -.5); d$ca <- d$c*d$a
for (re in c("(1+c*a|subj)", "(1+a+ca||subj)", "(1+c+a+ca||subj)")) {
  m <- lmer(as.formula(paste("agency_rating ~ c*a +", re)), d, control=lmerControl(optimizer="bobyqa"))
  cat("\n", re, " singular:", isSingular(m), " AIC(ML):", round(AIC(refitML(m)),1), "\n"); print(summary(m)$varcor)
  print(round(coef(summary(m))[, c(1,2,3,5)], 4)) }
