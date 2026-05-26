import { Router, Request, Response } from 'express';
import { body, validationResult } from 'express-validator';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import User from '../models/User';
import Session from '../models/Session';
import SkillProfile from '../models/SkillProfile';
import Career from '../models/Career';

const router = Router();
const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL || 'http://localhost:8000';
const AI_REQUEST_TIMEOUT_MS = Number(process.env.AI_REQUEST_TIMEOUT_MS || 30000);

// POST /api/assessment/start
router.post(
  '/start',
  [
    body('userId').isMongoId().withMessage('Valid User ID is required'),
    body('interests').isArray().withMessage('Interests must be an array'),
    body('skills').isArray().withMessage('Skills must be an array'),
  ],
  async (req: Request, res: Response): Promise<any> => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    try {
      const { userId, interests, skills } = req.body;

      const user = await User.findById(userId);
      if (!user) {
        return res.status(404).json({ error: 'User not found' });
      }

      // Determine domain from first interest or default
      const domain = interests.length > 0 ? interests[0].toLowerCase().replace(/ /g, '_') : 'general';

      let aiResponse;
      try {
        aiResponse = await axios.post(`${FASTAPI_BASE_URL}/api/generate-questions`, {
          domain,
          skills
        }, {
          timeout: AI_REQUEST_TIMEOUT_MS
        });
      } catch (error) {
        const detail = axios.isAxiosError(error)
          ? error.code === 'ECONNABORTED'
            ? `AI service timed out after ${AI_REQUEST_TIMEOUT_MS / 1000}s`
            : error.response?.data?.detail || error.response?.data?.error || error.message
          : 'AI service unavailable';

        console.error('Error calling AI service (/generate-questions):', detail);
        return res.status(502).json({ error: `AI question generation failed: ${detail}` });
      }

      const questions = aiResponse.data.questions;
      const total = aiResponse.data.total;
      const sessionId = uuidv4();

      const session = new Session({
        sessionId,
        userId,
        questions,
      });
      await session.save();

      return res.json({
        sessionId,
        questions,
        total
      });
    } catch (error) {
      console.error('Error starting assessment:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// POST /api/assessment/submit
router.post(
  '/submit',
  [
    body('userId').isMongoId().withMessage('Valid User ID is required'),
    body('sessionId').notEmpty().withMessage('Session ID is required'),
    body('answers').isArray().withMessage('Answers must be an array'),
  ],
  async (req: Request, res: Response): Promise<any> => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    try {
      const { userId, sessionId, answers } = req.body;

      const session = await Session.findOne({ sessionId, userId });
      if (!session) {
        return res.status(404).json({ error: 'Assessment session not found or expired' });
      }

      // Call Python scoring service
      let scoreResponse;
      try {
        scoreResponse = await axios.post(`${FASTAPI_BASE_URL}/api/score-assessment`, {
          answers
        });
      } catch (error) {
        console.error('Error calling AI service (/score-assessment):', error);
        return res.status(502).json({ error: 'AI service unavailable' });
      }

      const { skill_scores, level_per_skill, overall_level } = scoreResponse.data;

      // Fetch career dataset
      const careers = await Career.find({});
      const career_dataset = careers.map(c => ({
        role: c.role,
        requiredSkills: c.requiredSkills,
        demandScore: c.demandScore,
        description: c.description
      }));

      // Call Python recommend service
      let recommendResponse;
      try {
        recommendResponse = await axios.post(`${FASTAPI_BASE_URL}/api/recommend-careers`, {
          skill_scores,
          level_per_skill,
          overall_level,
          career_dataset
        });
      } catch (error) {
        console.error('Error calling AI service (/recommend-careers):', error);
        return res.status(502).json({ error: 'AI service unavailable' });
      }

      const recommendations = recommendResponse.data;

      // Save SkillProfile
      const skillProfile = new SkillProfile({
        userId,
        skillScores: skill_scores,
        levelPerSkill: level_per_skill,
        overallLevel: overall_level,
      });
      await skillProfile.save();

      // Clear session after submission
      await Session.deleteOne({ _id: session._id });

      return res.json({
        skillProfile,
        scoreDetails: scoreResponse.data,
        recommendations
      });
    } catch (error) {
      console.error('Error submitting assessment:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// GET /api/assessment/results/:userId
router.get(
  '/results/:userId',
  async (req: Request, res: Response): Promise<any> => {
    try {
      const { userId } = req.params;

      const skillProfile = await SkillProfile.findOne({ userId }).sort({ assessedAt: -1 });
      if (!skillProfile) {
        return res.status(404).json({ error: 'No skill profile found for this user' });
      }

      return res.json(skillProfile);
    } catch (error) {
      console.error('Error fetching results:', error);
      return res.status(500).json({ error: 'Internal server error' });
    }
  }
);

export default router;
